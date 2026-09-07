from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import _GeneratorContextManager, contextmanager
from typing import TYPE_CHECKING

from PySide6.QtCore import QMutex, QSize, QThread, QWaitCondition, Signal, Slot
from PySide6.QtGui import QOffscreenSurface, QOpenGLContext
from PySide6.QtOpenGL import QOpenGLFramebufferObject
from PySide6.QtQuick import QQuickFramebufferObject

from bingr.common.commonUtils import trimHeap

if TYPE_CHECKING:
    from mpv import MpvRenderContext

logger = logging.getLogger(__name__)

GL_COLOR_BUFFER_BIT = 0x4000

MPV_OPTIONS = {
    "vo": "libmpv",
    # "ao": "pulse",
    "hwdec": "auto-safe",
    # "audio-buffer": "3",
    # "profile": "gpu-hq",
    # "profile": "fast",  # "high-quality",
    # "deband": "no",
    "deband": "yes",
    # "cookies": "yes",
    # libmpv 0.37 (dev) rejects "auto" (added after 0.37; 0.41 flatpak accepts
    # it); "yes" is valid on both and bwdif passes progressive frames through.
    "deinterlace": "no",
    "cache": "auto",
    "cache_on_disk": "yes",
    # Balanced: fast startup without constant rebuffering on live HLS.
    # "cache_secs": 20,
    "cache_secs": 15,
    # "demuxer_max_bytes": "8MiB",
    # "demuxer_max_back_bytes": "3MiB",
    # "demuxer_max_bytes": "10MiB",
    # "demuxer_max_bytes": "50MiB",
    # "demuxer_readahead_secs": "10",
    # "demuxer_readahead_secs": "10",
    # "demuxer_readahead_secs": "5",
    # --------------------------------------
    # "demuxer-thread": "yes",
    "load_unsafe_playlists": True,
    # "hls_bitrate": "max",
    # "vd_queue_enable": "yes",
    # "ad_queue_enable": "yes",
    # --------------------------------------
    # Doubled from libavformat defaults (~5MB / ~5s) so streams with delayed
    # codec info (e.g. low-bitrate HLS variants) still get their parameters
    "demuxer_lavf_probesize": 15000000,
    "demuxer_lavf_analyzeduration": 15,
    "demuxer_lavf_o": "sub_text_format=srt",
    # "vd_lavc_threads": 3,
    # --------------------------------------
    "sub_auto": "no",
    "slang": "no",
    "subs_fallback": "no",
    "subs_fallback_forced": "no",
    "sub_create_cc_track": "yes",
    # "sub_fix_timing": "yes",
    # "sub_visibility": "yes",
    # "subs_fallback": "yes",
    # "subs_fallback_forced": "yes",
    # "sub_ass_override": "strip",
    # "embeddedfonts": "no",
    "demuxer_mkv_subtitle_preroll": "yes",
    "demuxer_mkv_subtitle_preroll_secs": "5.0",
    # removed in mpv 0.41 (OCS is a script now, not an option)
    # "osc": False,
    # "input_default_bindings": True,
    # "input_vo_keyboard": True,
    "volume": 50,
    # "replaygain": "track",
    # "replaygain_preamp": 0,
    # "replaygain_fallback": 5,
    # "af": "dynaudnorm=p=0.9:m=50:s=10:g=15",
    # "ytdl": "yes",
    "loglevel": "warn",
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def getProcAddress(_, name: bytes) -> int:
    ctx = QOpenGLContext.currentContext()
    return int(ctx.getProcAddress(name)) if ctx else 0


_MPV_LEVEL_MAP = {
    "fatal": logging.CRITICAL,
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "info": logging.INFO,
    "v": logging.DEBUG,
    "debug": logging.DEBUG,
    "trace": logging.DEBUG,
}

# Settings-UI values that need normalising to mpv's set_loglevel names.
_SETTINGS_LEVEL_MAP = {
    "none": "no",
}

_mpvLogger = logging.getLogger("bingr.mpv")


def _mpvLogHandler(level: str, prefix: str, text: str) -> None:
    """python-mpv log_handler callback — called on the MPV event thread.

    Receives structured (level, prefix, text) triples straight from libmpv's
    LOG_MESSAGE events; no stdout tunneling involved. logging is thread-safe.
    """
    if isinstance(text, bytes):
        text = text.decode(errors="replace")
    _mpvLogger.log(_MPV_LEVEL_MAP.get(level, logging.INFO), "[%s] %s", prefix, text.rstrip())


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
        self._lastSubSig: tuple | None = None
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
        self._logBuffer: list[str] = []

        self._parent.onSurfaceReady.connect(self._onConfigureSurface)

    def play(self, url: str):
        if self._disposed or not self._mpv:
            return
        self._lastSubSig = None
        self._mpv.play(url)

    def setPlaying(self, playing: bool):
        if self._disposed or not self._mpv:
            return
        self._mpv.pause = not playing

    def stopPlayback(self):
        if self._disposed or not self._mpv:
            return
        self._mpv.stop()

    def setVolume(self, vol: int):
        if self._disposed or not self._mpv:
            return
        self._mpv.volume = vol

    def setSubtitleTrack(self, trackId: int):
        if self._disposed or not self._mpv:
            logger.info("setSubtitleTrack: disposed=%s, mpv=%s — skipping", self._disposed, self._mpv is not None)
            return
        target = "no" if trackId == 0 else trackId
        self._mpv.sid = target
        try:
            actual = self._mpv.sid
        except Exception:
            actual = "<unreadable>"
        logger.info(
            "setSubtitleTrack: requested=%s, mpv.sid readback=%s",
            target,
            actual,
        )
        if self._renderThreadReady:
            self._renderThread.requestRender()

    @Slot()
    def _onConfigureSurface(self):
        self._surface.setFormat(self._surfaceFormat)
        self._surface.create()
        self._surfaceReady = True
        self._parent.update()  # type: ignore

    def _initializeMpvContext(self):
        if self._mpv:
            try:
                self._mpv.terminate()
                logger.debug("Terminated existing MPV before re-initialization")
            except Exception as e:
                logger.warning("Error terminating existing MPV before re-init: %s", e)
            self._mpv = None

        import locale

        import mpv

        # libmpv requires LC_NUMERIC=C; Qt resets the locale when it starts.
        # mpv.py sets this at import, but QApplication construction stomps it.
        locale.setlocale(locale.LC_NUMERIC, "C")

        opts = dict(MPV_OPTIONS)
        # opts["audio_delay"] = audio_delay
        # hwDecConfig = getHwDecConfig()
        # opts["hwdec"] = hwDecConfig.hwdec
        # opts["gpu_hwdec_interop"] = hwDecConfig.interop

        from bingr.common.config import getConfig

        cfg = getConfig()
        cacheDir = cfg.workspacePath() / "mpv-cache"
        cacheDir.mkdir(parents=True, exist_ok=True)
        opts["demuxer_cache_dir"] = str(cacheDir)

        try:
            from bingr.services.settingsService import SettingsService

            raw = SettingsService().get("advanced/mpvLogLevel", "warn")
            if isinstance(raw, str) and raw:
                opts["loglevel"] = _SETTINGS_LEVEL_MAP.get(raw, raw)
        except Exception as exc:
            _mpvLogger.warning("Could not read advanced/mpvLogLevel setting: %s", exc)

        logger.info("Final MPV options: %s", {k: v for k, v in opts.items() if k != "demuxer_lavf_o"})

        self._mpv: mpv.MPV = mpv.MPV(
            # log_handler=_mpvLogHandler,
            log_handler=print,
            # loglevel="debug",
            **opts,
        )

        self._mpv.demuxer_readahead_secs = 3

        self._mpv.observe_property("eof-reached", self._onEofReached)
        self._mpv.observe_property("demuxer-cache-duration", self._onCachedDuration)
        self._mpv.observe_property("demuxer-readahead-secs", self._onReadahead)
        self._mpv.observe_property("demuxer-cache-state", self._onDemuxerCacheState)
        self._mpv.observe_property("track-list", self._onTrackList)

        self._logBuffer.clear()
        self._mpv.register_event_callback(self._onMpvEvent)

        from mpv import MpvRenderContext

        self._ctx = MpvRenderContext(
            mpv=self._mpv,
            api_type="opengl",
            opengl_init_params={"get_proc_address": self._getProcAddressResolver},
        )
        self._ctx.update_cb = self._onMpvUpdate

        self._renderThread.prepare(self._ctx, QOpenGLContext.currentContext(), self._surface)
        self._renderThreadReady = True

        if self._parent._pendingUrl:
            self.play(self._parent._pendingUrl)
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

    @staticmethod
    def _subtitleDisplayName(t: dict) -> str:
        label = f"Sub {t['id']}"
        parts = []
        if t.get("title"):
            parts.append(t["title"])
        if t.get("lang"):
            parts.append(t["lang"].title())
        if t.get("hearing-impaired"):
            parts.append("Sdh")
        if t.get("visual-impaired"):
            parts.append("Ad")
        if t.get("forced"):
            parts.append("Forced")
        # if t.get("default"):
        #     parts.append("Default")
        if t.get("external"):
            parts.append("External")
        if parts:
            return f"{label} [{', '.join(parts)}]"
        return label

    def _onTrackList(self, _name, value):
        if self._disposed or value is None:
            return
        from bingr.ui_models.subtitleModel import SubtitleModel

        tracks = []
        for t in value:
            if t.get("type") == "sub":
                logger.info("track-list observer: %s", t)
                tracks.append(
                    SubtitleModel(
                        name=self._subtitleDisplayName(t),
                        trackId=t["id"],
                        langCode=t.get("lang", ""),
                    )
                )
        sig = tuple((t["id"], t.get("lang", "")) for t in value if t.get("type") == "sub")
        if sig == self._lastSubSig:
            logger.info(
                "_onTrackList: %s total, %s subtitle — dedup, not emitting",
                len(value),
                len(tracks),
            )
            return
        self._lastSubSig = sig
        logger.info(
            "_onTrackList: %s total, %s subtitle — emitting subtitleTracksChanged",
            len(value),
            len(tracks),
        )
        try:
            self._parent.subtitleTracksChanged.emit(tracks)
        except RuntimeError:
            pass
        logger.info("track-list observer: %s tracks total, %s subtitle", len(value), len(tracks))

    def _onMpvEvent(self, event):
        if self._disposed:
            return
        import mpv as _mpv

        eid = event.event_id.value

        if eid == int(_mpv.MpvEventID.END_FILE):
            end_file = event.data
            reason = getattr(end_file, "reason", None)
            if reason is not None and int(reason) == int(_mpv.MpvEventEndFile.ERROR):
                error_code = getattr(end_file, "error", None) or 0
                title, detail = self._buildErrorMessage(int(error_code))
                logger.debug("mpv END_FILE error: %s — %s", title, detail)
                try:
                    self._parent.errorOccurred.emit(title, detail)
                except RuntimeError:
                    pass
                self._logBuffer.clear()

        elif eid == int(_mpv.MpvEventID.LOG_MESSAGE):
            ev = event.data
            level = ev.level if isinstance(ev.level, str) else str(ev.level)
            if level in ("error", "warn"):
                prefix = ev.prefix if isinstance(ev.prefix, str) else str(ev.prefix)
                text = ev.text if isinstance(ev.text, str) else str(ev.text)
                line = f"[{prefix}] {text}".strip()
                if line and len(self._logBuffer) < 20:
                    self._logBuffer.append(line)

    @staticmethod
    def _mpvErrorTitle(error_code: int) -> str:
        import mpv as _mpv

        ec = _mpv.ErrorCode
        if error_code == ec.LOADING_FAILED:
            return "Stream Unavailable"
        if error_code == ec.NOTHING_TO_PLAY:
            return "No Playable Streams"
        if error_code == ec.UNKNOWN_FORMAT:
            return "Unsupported Format"
        if error_code == ec.VO_INIT_FAILED:
            return "Video Output Error"
        if error_code == ec.AO_INIT_FAILED:
            return "Audio Output Error"
        return "Playback Error"

    def _buildErrorMessage(self, error_code: int) -> tuple[str, str]:
        import mpv as _mpv

        title = self._mpvErrorTitle(error_code)

        detail = self._extractErrorDetail()

        if not detail:
            ec = _mpv.ErrorCode
            if error_code == ec.LOADING_FAILED:
                detail = "The stream could not be loaded.\nThe URL may be invalid, offline, or returning an error."
            elif error_code == ec.NOTHING_TO_PLAY:
                detail = "No audio or video streams were found in this source."
            elif error_code == ec.UNKNOWN_FORMAT:
                detail = "The stream format could not be recognized."
            elif error_code == ec.VO_INIT_FAILED:
                detail = "Failed to initialize video output."
            elif error_code == ec.AO_INIT_FAILED:
                detail = "Failed to initialize audio output."
            else:
                detail = "An error occurred during playback."

        return title, detail

    def _extractErrorDetail(self) -> str:
        if not self._logBuffer:
            return ""

        handlers = (
            self._matchHttpError,
            self._matchOpenFailure,
            self._matchNetworkError,
            self._matchStreamLogError,
        )
        for match in handlers:
            line = match()
            if line is not None:
                return self._humanize(line)
        return self._humanize(self._logBuffer[-1])

    def _matchHttpError(self) -> str | None:
        for line in self._logBuffer:
            lower = line.lower()
            if "http" in lower and ("error" in lower or "fail" in lower):
                if self._humanHttpError(line):
                    return line
        return None

    def _matchOpenFailure(self) -> str | None:
        for line in self._logBuffer:
            if self._looksLikeOpenFailure(line.lower()):
                return line
        return None

    def _matchNetworkError(self) -> str | None:
        for line in self._logBuffer:
            if self._looksLikeNetworkError(line.lower()):
                return line
        return None

    def _matchStreamLogError(self) -> str | None:
        for line in self._logBuffer:
            lower = line.lower()
            if any(prefix in lower for prefix in ("ffmpeg", "stream", "demux")) and (
                "error" in lower or "fail" in lower
            ):
                return line
        return None

    def _humanize(self, line: str) -> str:
        lower = line.lower()
        if "http" in lower and ("error" in lower or "fail" in lower):
            msg = self._humanHttpError(line)
            if msg:
                return msg
        if self._looksLikeNetworkError(lower):
            return self._humanNetworkError(line)
        return self._humanStreamError(line)

    @staticmethod
    def _looksLikeOpenFailure(lower: str) -> bool:
        return "failed to open" in lower or "could not open" in lower or "not open" in lower

    @staticmethod
    def _looksLikeNetworkError(lower: str) -> bool:
        keywords = ("connection", "resolve", "timed out", "refused", "reset")
        return any(kw in lower for kw in keywords)

    @staticmethod
    def _humanHttpError(line: str) -> str:
        clean = line.split("] ", 1)[-1] if "] " in line else line
        import re

        match = re.search(r"\b(4\d\d|5\d\d)\b", clean)
        if not match:
            return ""
        code = match.group(1)
        known = {
            "401": "Authorization required",
            "403": "Access denied",
            "404": "Not found",
            "408": "Request timed out",
            "410": "Gone",
            "429": "Too many requests",
            "500": "Internal server error",
            "502": "Bad gateway",
            "503": "Service unavailable",
            "504": "Gateway timeout",
        }
        reason = known.get(code, "")
        if reason:
            return f"The stream server returned HTTP {code} ({reason}). The channel may be temporarily unavailable — try again in a moment."
        return f"The stream server returned HTTP {code}. The channel could not be loaded."

    @staticmethod
    def _humanNetworkError(line: str) -> str:
        clean = line.split("] ", 1)[-1] if "] " in line else line
        lower = clean.lower()
        if "timed out" in lower or "timeout" in lower:
            return "Connection timed out. The stream server may be unreachable or overloaded — check your network and try again."
        if "refused" in lower:
            return "Connection refused. The stream server is not accepting connections right now."
        if "resolve" in lower or "host not found" in lower or "name or service not known" in lower:
            return "Could not resolve the stream server address. Check your internet connection or the stream URL."
        if "reset" in lower:
            return "The connection was reset before the stream could load. Try again in a moment."
        return "A network problem prevented the stream from loading. Check your connection and try again."

    @staticmethod
    def _humanStreamError(line: str) -> str:
        clean = line.split("] ", 1)[-1] if "] " in line else line
        lower = clean.lower()
        if "failed to open" in lower or "not open" in lower or "could not open" in lower:
            return "Could not open this channel. The stream may be offline, the URL may have changed, or the server restricts access."
        if "no data" in lower or "empty" in lower or "no stream" in lower:
            return "The stream returned no playable data. The channel may be offline."
        if "unsupported" in lower or "unknown format" in lower:
            return "The stream format is not supported by the player."
        return (
            "An unexpected error occurred while loading this channel. Please try another channel or try again shortly."
        )

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
        try:
            self._mpv.unregister_event_callback(self._onMpvEvent)
        except Exception:
            pass
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
        trimHeap()

    def _detachFromParent(self):
        if self._parent is None:
            return
        try:
            self._parent.onSurfaceReady.disconnect(self._onConfigureSurface)
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
