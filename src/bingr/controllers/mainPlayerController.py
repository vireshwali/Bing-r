from __future__ import annotations

import asyncio
import logging
from collections.abc import Generator
from contextlib import _GeneratorContextManager, contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Property, QMutex, QObject, QSize, QThread, QTimer, QWaitCondition, Signal, Slot
from PySide6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext
from PySide6.QtOpenGL import QOpenGLFramebufferObject
from PySide6.QtQml import QmlElement, QQmlEngine, qmlEngine
from PySide6.QtQuick import QQuickFramebufferObject

from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.services.watchSessionService import WatchSessionService
from bingr.ui_models.streamModel import StreamModel
from bingr.ui_models.streamsViewModel import StreamsViewModel
from bingr.utils.hwDec import getHwDecConfig

if TYPE_CHECKING:
    from mpv import MpvRenderContext

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

GL_COLOR_BUFFER_BIT = 0x4000

MIN_WATCH_SESSION_SECONDS = 30

MPV_OPTIONS = {
    "vo": "libmpv",
    "ao": "pulse",
    "hwdec": "auto-safe",
    "audio-buffer": "3",
    # "profile": "gpu-hq",
    "profile": "fast",
    "deband": "no",
    "cache_secs": 20,
    "demuxer_max_bytes": "10MiB",
    "demuxer_max_back_bytes": "4MiB",
    "demuxer_readahead_secs": "5",
    "demuxer_thread": "yes",
    "load-unsafe-playlists": True,
    "hls_bitrate": "min",
    "vd_lavc_threads": 2,
    "loglevel": "warn",
    # removed in mpv 0.41 (OCS is a script now, not an option)
    # "osc": False,
    "input_default_bindings": True,
    "input_vo_keyboard": True,
    "volume": 50,
    "replaygain": "track",
    "replaygain_preamp": 0,
    "replaygain_fallback": 5,
    "af": "dynaudnorm=p=0.9:m=50:s=10:g=15",
}


def getProcAddress(_, name: bytes) -> int:
    ctx = QOpenGLContext.currentContext()
    return int(ctx.getProcAddress(name)) if ctx else 0


class RenderState:
    def __init__(self):
        self._renderFBO: QOpenGLFramebufferObject | None = None
        self._displayFBO: QOpenGLFramebufferObject | None = None
        self._videoSize = QSize()
        self._shouldRender = False
        self._renderingActive = True

    @property
    def renderFBO(self) -> QOpenGLFramebufferObject | None:
        return self._renderFBO

    @property
    def displayFBO(self) -> QOpenGLFramebufferObject | None:
        return self._displayFBO

    @property
    def videoSize(self) -> QSize:
        return self._videoSize

    @property
    def shouldRender(self) -> bool:
        return self._shouldRender

    @property
    def renderingActive(self) -> bool:
        return self._renderingActive

    def requestRender(self) -> None:
        self._shouldRender = True

    def clearRenderRequest(self) -> None:
        self._shouldRender = False

    def updateVideoSize(self, size: QSize) -> bool:
        if self._videoSize != size:
            self._videoSize = size
            self._shouldRender = True
            return True
        return False

    def setFBOs(self, renderFBO, displayFBO):
        self._renderFBO = renderFBO
        self._displayFBO = displayFBO

    def swapFBOs(self):
        self._renderFBO, self._displayFBO = self._displayFBO, self._renderFBO

    def clearFBOs(self):
        if self._renderFBO is not None:
            del self._renderFBO
            self._renderFBO = None
        if self._displayFBO is not None:
            del self._displayFBO
            self._displayFBO = None

    def stopRendering(self) -> None:
        self._renderingActive = False

    def needsFboRecreation(self, targetSize: QSize) -> bool:
        return (
            self._renderFBO is None
            or self._renderFBO.size() != targetSize
            or self._displayFBO is None
            or self._displayFBO.size() != targetSize
        )


class ThreadSync:
    def __init__(self):
        self._mutex = QMutex()
        self._waitCondition = QWaitCondition()

    def lock(self):
        self._mutex.lock()

    def unlock(self):
        self._mutex.unlock()

    def wait(self):
        self._waitCondition.wait(self._mutex)

    def wakeOne(self):
        self._waitCondition.wakeOne()


class SynchronizedState:
    def __init__(self):
        self._state: RenderState = RenderState()
        self._sync: ThreadSync = ThreadSync()

    @contextmanager
    def locked(self) -> Generator[tuple[RenderState, ThreadSync], None, None]:
        self._sync.lock()
        try:
            yield self._state, self._sync
        finally:
            self._sync.unlock()


class MpvOffscreenRenderThread(QThread):
    frameRendered = Signal()

    def __init__(self):
        super().__init__()
        self._ctx: MpvRenderContext | None = None
        self._surface: QOffscreenSurface | None = None
        self._sharedContext: QOpenGLContext | None = None
        self._glContext: QOpenGLContext | None = None
        self._synchronizedState: SynchronizedState = SynchronizedState()

    def acquire(self) -> _GeneratorContextManager[tuple[RenderState, ThreadSync]]:
        return self._synchronizedState.locked()

    def prepare(self, ctx, sharedContext, surface):
        self._ctx = ctx
        self._sharedContext = sharedContext
        self._surface = surface

    def requestRender(self):
        with self.acquire() as (state, sync):
            state.requestRender()
            sync.wakeOne()

    def updateSize(self, size: QSize):
        with self.acquire() as (state, sync):
            state.updateVideoSize(size)
            sync.wakeOne()

    def run(self):
        if not self._surface or not self._sharedContext:
            return

        self._glContext = QOpenGLContext()
        self._glContext.setFormat(self._surface.format())
        self._glContext.setShareContext(self._sharedContext)

        if not self._glContext.create():
            return

        if not self._glContext.makeCurrent(self._surface):
            return

        try:
            self._renderLoop()
        finally:
            self._glContext.doneCurrent()

    def _renderLoop(self):
        while True:
            with self.acquire() as (state, sync):
                while not state.shouldRender:
                    if not state.renderingActive:
                        return
                    sync.wait()

                if not state.renderingActive:
                    break

                shouldRender = state.shouldRender
                state.clearRenderRequest()
                videoSize = QSize(state.videoSize)

            if not shouldRender or not self._ctx:
                continue

            with self.acquire() as (state, sync):
                recreate = state.needsFboRecreation(videoSize)

            if recreate:
                newRenderFBO = QOpenGLFramebufferObject(videoSize)
                newDisplayFBO = QOpenGLFramebufferObject(videoSize)

                gl = QOpenGLContext.currentContext().functions()
                for fbo in (newRenderFBO, newDisplayFBO):
                    fbo.bind()
                    gl.glClearColor(0.0, 0.0, 0.0, 1.0)
                    gl.glClear(GL_COLOR_BUFFER_BIT)
                    fbo.release()

                fboHandle = int(newRenderFBO.handle())
                self._ctx.render(
                    flip_y=False,
                    opengl_fbo={"w": videoSize.width(), "h": videoSize.height(), "fbo": fboHandle},
                )
                QOpenGLContext.currentContext().functions().glFlush()

                with self.acquire() as (state, sync):
                    oldRenderFBO = state.renderFBO
                    oldDisplayFBO = state.displayFBO
                    state.setFBOs(newRenderFBO, newDisplayFBO)
                    state.swapFBOs()

                if oldRenderFBO:
                    del oldRenderFBO
                if oldDisplayFBO:
                    del oldDisplayFBO
            else:
                with self.acquire() as (state, sync):
                    fboHandle = int(state.renderFBO.handle())

                self._ctx.render(
                    flip_y=False,
                    opengl_fbo={"w": videoSize.width(), "h": videoSize.height(), "fbo": fboHandle},
                )
                QOpenGLContext.currentContext().functions().glFlush()

                with self.acquire() as (state, sync):
                    state.swapFBOs()

            self.frameRendered.emit()

    def stop(self):
        with self.acquire() as (state, sync):
            state.stopRendering()
            sync.wakeOne()
        self.wait()

    def cleanup(self):
        with self.acquire() as (state, _sync):
            state.clearFBOs()

        if self._glContext:
            try:
                if QOpenGLContext.currentContext() is self._glContext:
                    self._glContext.doneCurrent()
                logger.debug("Render thread GL context released")
            except Exception as e:
                logger.warning("Error releasing render thread GL context: %s", e)
            self._glContext = None

        self._ctx = None
        self._surface = None
        self._sharedContext = None


class MpvOffscreenRenderer(QQuickFramebufferObject.Renderer):
    def __init__(self, parent):
        super().__init__()
        from mpv import MpvGlGetProcAddressFn

        self._parent = parent
        self._disposed = False
        self._getProcAddressResolver = MpvGlGetProcAddressFn(getProcAddress)
        self._ctx: MpvRenderContext | None = None
        self._mpv = None
        self._videoSize = QSize()

        self._renderThread: MpvOffscreenRenderThread = MpvOffscreenRenderThread()
        self._renderThread.frameRendered.connect(self._parent.requestUpdate)
        self._renderThreadReady = False

        self._surface: QOffscreenSurface = QOffscreenSurface()
        self._surfaceFormat = QOpenGLContext.currentContext().format()
        self._surfaceReady = False
        self._rendererThreadStarted = False

        self._parent.onSurfaceReady.connect(self._onConfigureSurface)

    @Slot()
    def _onConfigureSurface(self):
        self._surface.setFormat(self._surfaceFormat)
        self._surface.create()
        self._surfaceReady = True
        self._parent.update()  # type: ignore

    def _initializeMpvContext(self):
        if self._mpv:
            try:
                self._mpv.stop()
                logger.debug("Stopped existing MPV before re-initialization")
            except Exception as e:
                logger.warning("Error stopping existing MPV before re-init: %s", e)
            self._mpv = None

        import locale

        import mpv

        # libmpv requires LC_NUMERIC=C; Qt resets the locale when it starts.
        # mpv.py sets this at import, but QApplication construction stomps it.
        locale.setlocale(locale.LC_NUMERIC, "C")

        refresh = QGuiApplication.primaryScreen().refreshRate() or 60
        audio_delay = -(1.0 / refresh) / 2.0

        opts = dict(MPV_OPTIONS)
        opts["audio_delay"] = audio_delay
        hwDecConfig = getHwDecConfig()
        opts["hwdec"] = hwDecConfig.hwdec
        opts["gpu-hwdec-interop"] = hwDecConfig.interop

        # settings = SettingsService(self)
        # bufferSeconds = settings.get("playback/bufferSeconds", 20)
        # defaultVolume = settings.get("playback/defaultVolume", 50)
        # mpvLogLevel = settings.get("advanced/mpvLogLevel", "warn")
        # opts["cache_secs"] = bufferSeconds
        # opts["volume"] = defaultVolume
        # opts["loglevel"] = mpvLogLevel

        self._mpv: mpv.MPV = mpv.MPV(
            log_handler=print,
            **opts,
        )

        self._mpv.demuxer_readahead_secs = 3

        self._mpv.observe_property("eof-reached", self._onEofReached)
        self._mpv.observe_property("demuxer-cache-duration", self._onCachedDuration)
        self._mpv.observe_property("demuxer-readahead-secs", self._onReadahead)
        self._mpv.observe_property("demuxer-cache-state", self._onDemuxerCacheState)

        from mpv import MpvRenderContext

        self._ctx = MpvRenderContext(
            mpv=self._mpv,
            api_type="opengl",
            opengl_init_params={"get_proc_address": self._getProcAddressResolver},
        )
        self._ctx.update_cb = self._onMpvUpdate

        self._renderThread.prepare(self._ctx, QOpenGLContext.currentContext(), self._surface)
        self._renderThreadReady = True

        self._parent._mpv = self._mpv

        if self._parent._pendingUrl:
            self._mpv.play(self._parent._pendingUrl)
            self._parent._pendingUrl = None

    def _onMpvUpdate(self):
        if self._disposed:
            return
        if self._renderThreadReady:
            self._renderThread.requestRender()

    def _onEofReached(self, _name, value):
        if self._disposed:
            return
        if value:
            self._parent._scheduleReconnect()

    def _emitSignal(self, signal, value):
        try:
            signal.emit(value)
        except RuntimeError:
            pass

    def _onCachedDuration(self, _name, value):
        if self._disposed:
            return
        try:
            self._emitSignal(self._parent.bufferedSecondsChanged, float(value or 0.0))
        except (ValueError, TypeError):
            self._emitSignal(self._parent.bufferedSecondsChanged, 0.0)

    def _onReadahead(self, _name, value):
        if self._disposed:
            return
        try:
            self._emitSignal(self._parent.readaheadSecsChanged, float(value or 0.0))
        except (ValueError, TypeError):
            self._emitSignal(self._parent.readaheadSecsChanged, 0.0)

    def _onDemuxerCacheState(self, _name, value):
        if self._disposed:
            return
        if not isinstance(value, dict):
            self._emitSignal(self._parent.bufferingStateChanged, "idle")
            return
        underrun = bool(value.get("underrun", False))
        self._emitSignal(self._parent.bufferingStateChanged, "buffering" if underrun else "playing")
        if not underrun and self._mpv and hasattr(self._mpv, "demuxer_readahead_secs"):
            current = self._mpv.demuxer_readahead_secs
            if current is not None and current < 39:
                self._mpv.demuxer_readahead_secs = 40

    def createFramebufferObject(self, size: QSize):
        if self._disposed:
            return QQuickFramebufferObject.Renderer.createFramebufferObject(self, size)

        if self._mpv is None:
            self._initializeMpvContext()

        if self._videoSize != size:
            self._videoSize = size
            if self._renderThreadReady:
                self._renderThread.updateSize(size)

        return QQuickFramebufferObject.Renderer.createFramebufferObject(self, size)

    def render(self):
        if self._disposed:
            return

        if not self._surfaceReady:
            self._parent.onSurfaceReady.emit()
            return

        if not self._renderThreadReady:
            return

        if not self._rendererThreadStarted:
            self._renderThread.start()
            self._rendererThreadStarted = True
            return

        with self._renderThread.acquire() as (state, _sync):
            displayFBO = state.displayFBO
            if displayFBO and displayFBO.isValid():
                QOpenGLFramebufferObject.blitFramebuffer(self.framebufferObject(), displayFBO)

    def cleanup(self):
        self._disposed = True

        # Teardown order matters: the render thread must stop and the mpv
        # render context must be freed BEFORE the libmpv core is destroyed,
        # otherwise the render thread or the render context can still touch
        # the freed core (use-after-free crash).
        self._teardownRenderThread()
        self._teardownRenderContext()
        self._teardownMpv()
        self._detachFromParent()
        self._teardownSurface()

        self._parent = None

    def _teardownMpv(self):
        if not self._mpv:
            return
        for name, handler in (
            ("eof-reached", self._onEofReached),
            ("demuxer-cache-duration", self._onCachedDuration),
            ("demuxer-readahead-secs", self._onReadahead),
            ("demuxer-cache-state", self._onDemuxerCacheState),
        ):
            try:
                self._mpv.unobserve_property(name, handler)
            except Exception as e:
                logger.warning("Error unregistering MPV observer %s: %s", name, e)

        try:
            self._mpv.stop()
            logger.debug("MPV stopped in renderer cleanup")
        except Exception as e:
            logger.warning("Error stopping MPV in cleanup: %s", e)

        try:
            self._mpv.terminate()
            logger.debug("MPV terminated in renderer cleanup")
        except Exception as e:
            logger.warning("Error terminating MPV in cleanup: %s", e)
        self._mpv = None

    def _detachFromParent(self):
        if self._parent is None:
            return
        try:
            self._parent.onSurfaceReady.disconnect(self._onConfigureSurface)
        except Exception:
            pass
        try:
            self._parent._mpv = None
        except Exception:
            pass

    def _teardownRenderThread(self):
        if not self._renderThread:
            return
        try:
            self._renderThread.stop()
            self._renderThread.cleanup()
            logger.debug("Render thread stopped and cleaned up")
        except Exception as e:
            logger.warning("Error stopping render thread: %s", e)
        self._renderThread = None

    def _teardownRenderContext(self):
        if not self._ctx:
            return
        try:
            self._ctx.free()
            logger.debug("MPV render context freed")
        except Exception as e:
            logger.warning("Error freeing render context: %s", e)
        self._ctx = None

    def _teardownSurface(self):
        if not self._surface:
            return
        try:
            self._surface.destroy()
            logger.debug("Offscreen surface destroyed")
        except Exception as e:
            logger.warning("Error destroying surface: %s", e)
        self._surface = None


@QmlElement
class MpvFramebufferObject(QQuickFramebufferObject):
    requestUpdate = Signal()
    onSurfaceReady = Signal()

    bufferedSecondsChanged = Signal(float)
    readaheadSecsChanged = Signal(float)
    bufferingStateChanged = Signal(str)
    errorOccurred = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._mpv = None
        self._renderer: MpvOffscreenRenderer | None = None
        self._pendingUrl: str | None = None
        self._reconnectAttempt = 0
        self._maxReconnectAttempts = 5
        self._mediaUrl: str | None = None
        self._userPaused = False

        self.requestUpdate.connect(self.doUpdate)
        self.destroyed.connect(self._onDestroyed)

    @Slot()
    def doUpdate(self):
        self.update()

    @Slot()
    def _onDestroyed(self):
        if self._renderer:
            self._renderer.cleanup()
            self._renderer = None

    def createRenderer(self):
        self._renderer = MpvOffscreenRenderer(self)
        return self._renderer

    # ---- Public slots called from QML ----

    @Slot(str)
    def setMediaUrl(self, url: str):
        self._mediaUrl = url
        if self._mpv:
            try:
                self._mpv.play(url)
                logger.debug("Switched stream to: %s", url)
            except Exception as e:
                logger.warning("Error switching stream: %s", e)
        else:
            self._pendingUrl = url

    @Slot(bool)
    def setPlaying(self, playing: bool):
        self._userPaused = not playing
        if self._mpv:
            self._mpv.pause = not playing

    @Slot()
    def stop(self):
        self._mediaUrl = ""
        self._userPaused = False
        logger.info("Explicit stop() called on MpvFramebufferObject")

        if self._renderer:
            try:
                self._renderer.cleanup()
                logger.debug("Renderer cleanup completed via stop()")
            except Exception as e:
                logger.warning("Error in renderer cleanup during stop(): %s", e)
            self._renderer = None

        if self._mpv:
            try:
                self._mpv.stop()
            except Exception as e:
                logger.warning("Error stopping MPV directly in stop(): %s", e)
            self._mpv = None

    @Slot(int)
    def setVolume(self, vol: int):
        if self._mpv:
            self._mpv.volume = vol

    # ---- Reconnection ----

    def _scheduleReconnect(self):
        self._reconnectAttempt += 1
        if self._reconnectAttempt <= self._maxReconnectAttempts:
            delay = 2**self._reconnectAttempt
            print(f"[MPV] Reconnecting in {delay}s (attempt {self._reconnectAttempt}/{self._maxReconnectAttempts})")
            QTimer.singleShot(delay * 1000, self._doReconnect)

    def _doReconnect(self):
        if self._mpv and self._mediaUrl:
            print(f"[MPV] Reconnecting to {self._mediaUrl}")
            self._mpv.play(self._mediaUrl)


@QmlElement
class MainPlayerController(QObject):
    # Signals
    currentStreamIndexChanged = Signal(int)
    playingChanged = Signal(bool)
    playUrlRequested = Signal(str)
    volumeChanged = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.appEngine: QQmlEngine | None = qmlEngine(self)
        self._channelId = -1
        self._streamUrls: list[StreamModel] = []
        self._currentStreamIndex = 0
        self._playing = False
        self._volume = 50
        self._service = ChannelsManagementService()
        self._streamsViewModel = StreamsViewModel(self)
        self._watchService = WatchSessionService()
        self._sessionStartTime: datetime | None = None
        self._sessionChannelId: int = -1

    @Property(int)
    def channelId(self) -> int:
        return self._channelId

    @channelId.setter
    def channelId(self, value: int) -> None:
        if value != self._channelId:
            self._channelId = value
            logger.info("Channel Id set to: %s", self._channelId)

    @Property(QObject, constant=True)
    def streamsViewModel(self) -> QObject:
        return self._streamsViewModel

    @Property(int, notify=currentStreamIndexChanged)
    def currentStreamIndex(self) -> int:
        return self._currentStreamIndex

    @currentStreamIndex.setter
    def currentStreamIndex(self, value: int) -> None:
        if value != self._currentStreamIndex and 0 <= value < len(self._streamUrls):
            self._currentStreamIndex = value
            self.currentStreamIndexChanged.emit(value)

    @Property(bool, notify=playingChanged)
    def playing(self) -> bool:
        return self._playing

    @Property(int, notify=volumeChanged)
    def volume(self) -> int:
        return self._volume

    @Slot(int)
    def setVolume(self, sliderVal: int):
        mpvVol = max(0, min(100, sliderVal))
        if mpvVol != self._volume:
            self._volume = mpvVol
            self.volumeChanged.emit(self._volume)

    @Slot(int)
    def openChannel(self, channelId: int):
        self._endCurrentSession(completed=False)
        asyncio.ensure_future(self._loadAndPlay(channelId))  # noqa: RUF006

    @Slot()
    def stop(self):
        """Stop playback and persist any active watch session."""
        self._endCurrentSession(completed=True)
        self._playing = False
        self.playingChanged.emit(False)

    def _endCurrentSession(self, completed: bool) -> None:
        """Persist the active watch session if it lasted long enough.

        Uses the channel captured at session start (``_sessionChannelId``),
        NOT the current ``_channelId`` — so rapid channel switching can never
        attribute an old session to a newly opened channel. State is reset
        before the async DB write so a follow-up switch starts clean.
        """
        if self._sessionStartTime is None or self._sessionChannelId == -1:
            return

        startedAt = self._sessionStartTime
        channelId = self._sessionChannelId

        self._sessionStartTime = None
        self._sessionChannelId = -1

        endedAt = datetime.now(UTC)
        durationSeconds = int((endedAt - startedAt).total_seconds())
        if durationSeconds < MIN_WATCH_SESSION_SECONDS:
            logger.debug("Watch session too short (%ds) — discarding", durationSeconds)
            return

        asyncio.ensure_future(  # noqa: RUF006
            self._watchService.recordSession(
                channelId,
                startedAt.isoformat(),
                endedAt.isoformat(),
                durationSeconds,
                completed,
            )
        )

    async def _loadAndPlay(self, channelId: int):
        logger.info("Loading streams for channel %s", channelId)
        streams = await self._service.getM3uStreamsWithMeta(channelId)
        if not streams:
            logger.warning("No streams found for channel %s", channelId)
            return
        self._streamUrls = streams
        self._currentStreamIndex = 0
        self._streamsViewModel.resetItems(streams)
        self.currentStreamIndexChanged.emit(0)
        self.playUrlRequested.emit(streams[0].url)
        logger.info("Playing stream 0/%s: %s", len(streams), streams[0].url)

        asyncio.ensure_future(self._service.incrementVisitCount(channelId))  # noqa: RUF006

    @Slot(int)
    def switchStream(self, index: int):
        if index == self._currentStreamIndex:
            return
        if 0 <= index < len(self._streamUrls):
            self._currentStreamIndex = index
            self.currentStreamIndexChanged.emit(index)
            self.playUrlRequested.emit(self._streamUrls[index].url)
            logger.info(
                "Switched to stream %s/%s: %s",
                index,
                len(self._streamUrls),
                self._streamUrls[index].url,
            )

    @Slot(bool)
    def setPlaying(self, playing: bool):
        if playing and self._sessionStartTime is None:
            self._sessionStartTime = datetime.now(UTC)
            self._sessionChannelId = self._channelId
            logger.info("Watch session started for channel %s", self._sessionChannelId)
        self._playing = playing
        self.playingChanged.emit(playing)
