from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QQmlEngine, qmlEngine
from PySide6.QtQuick import QQuickFramebufferObject

from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.services.mainPlayerService import MpvOffscreenRenderer
from bingr.services.watchSessionService import WatchSessionService
from bingr.ui_models.streamModel import StreamModel
from bingr.ui_models.streamsViewModel import StreamsViewModel
from bingr.ui_models.subtitleModel import SubtitleModel
from bingr.ui_models.subtitlesViewModel import SubtitlesViewModel

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

MIN_WATCH_SESSION_SECONDS = 30


@QmlElement
class MpvFramebufferObject(QQuickFramebufferObject):
    requestUpdate = Signal()
    onSurfaceReady = Signal()

    bufferedSecondsChanged = Signal(float)
    readaheadSecsChanged = Signal(float)
    bufferingStateChanged = Signal(str)
    errorOccurred = Signal(str, str)
    subtitleTracksChanged = Signal(list)

    def __init__(self):
        super().__init__()
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
        if self._renderer:
            try:
                self._renderer.play(url)
                logger.debug("Switched stream to: %s", url)
            except Exception as e:
                logger.warning("Error switching stream: %s", e)
                QTimer.singleShot(
                    0,
                    lambda msg=str(e): self.errorOccurred.emit("Stream Error", msg),
                )
        else:
            self._pendingUrl = url

    @Slot(bool)
    def setPlaying(self, playing: bool):
        self._userPaused = not playing
        if self._renderer:
            self._renderer.setPlaying(playing)

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

    @Slot(int)
    def setVolume(self, vol: int):
        if self._renderer:
            self._renderer.setVolume(vol)

    @Slot(int)
    def setSubtitleTrack(self, trackId: int):
        logger.info(
            "MpvFramebufferObject.setSubtitleTrack: trackId=%d, renderer=%s", trackId, self._renderer is not None
        )
        if self._renderer:
            self._renderer.setSubtitleTrack(trackId)

    # ---- Reconnection ----

    def _scheduleReconnect(self):
        self._reconnectAttempt += 1
        if self._reconnectAttempt <= self._maxReconnectAttempts:
            delay = 2**self._reconnectAttempt
            logger.info(
                "Reconnecting in %ss (attempt %d/%d)",
                delay,
                self._reconnectAttempt,
                self._maxReconnectAttempts,
            )
            QTimer.singleShot(delay * 1000, self, self._doReconnect)
        else:
            logger.warning("Max reconnect attempts (%d) reached for %s", self._maxReconnectAttempts, self._mediaUrl)
            try:
                self.errorOccurred.emit(
                    "Stream Disconnected",
                    f"Connection lost and could not be restored after {self._maxReconnectAttempts} attempts.",
                )
            except RuntimeError:
                pass

    def _doReconnect(self):
        if self._renderer and self._mediaUrl:
            logger.info("Reconnecting to %s", self._mediaUrl)
            self._renderer.play(self._mediaUrl)


@QmlElement
class MainPlayerController(QObject):
    # Signals
    currentStreamIndexChanged = Signal(int)
    playingChanged = Signal(bool)
    playUrlRequested = Signal(str)
    volumeChanged = Signal(int)
    hasMultipleStreamsChanged = Signal(bool)
    currentSubtitleIndexChanged = Signal(int)
    hasSubtitlesChanged = Signal(bool)
    subtitleTrackChanged = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.appEngine: QQmlEngine | None = qmlEngine(self)
        self._channelId = -1
        self._streamUrls: list[StreamModel] = []
        self._currentStreamIndex = 0
        self._playing = False
        self._volume = 50
        self._hasMultipleStreams = False
        self._service = ChannelsManagementService()
        self._streamsViewModel: Any = StreamsViewModel(self)  # type: ignore[reportCallIssue]
        self._subtitlesViewModel: Any = SubtitlesViewModel(self)  # type: ignore[reportCallIssue]
        self._subtitleTracks: list[SubtitleModel] = []
        self._currentSubtitleIndex = 0
        self._hasSubtitles = False
        self._userSelectedSub = False
        self._watchService = WatchSessionService()
        self._sessionStartTime: datetime | None = None
        self._sessionChannelId: int = -1

    @Property(bool, notify=hasMultipleStreamsChanged)
    def hasMultipleStreams(self) -> bool:
        return self._hasMultipleStreams

    @Property(int)
    def channelId(self) -> int:  # type: ignore[reportRedeclaration]
        return self._channelId

    @channelId.setter
    def channelId(self, value: int) -> None:
        if value != self._channelId:
            self._channelId = value
            logger.info("Channel Id set to: %s", self._channelId)

    @Property(QObject, constant=True)
    def streamsViewModel(self) -> QObject:
        return self._streamsViewModel

    @Property(QObject, constant=True)
    def subtitlesViewModel(self) -> QObject:
        return self._subtitlesViewModel

    @Property(int, notify=currentStreamIndexChanged)
    def currentStreamIndex(self) -> int:  # type: ignore[reportRedeclaration]
        return self._currentStreamIndex

    @currentStreamIndex.setter
    def currentStreamIndex(self, value: int) -> None:
        if value != self._currentStreamIndex and 0 <= value < len(self._streamUrls):
            self._currentStreamIndex = value
            self.currentStreamIndexChanged.emit(value)

    @Property(int, notify=currentSubtitleIndexChanged)
    def currentSubtitleIndex(self) -> int:
        return self._currentSubtitleIndex

    @Property(bool, notify=hasSubtitlesChanged)
    def hasSubtitles(self) -> bool:
        return self._hasSubtitles

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
        self._resetSubtitleState()
        self._playing = False
        self._setHasMultipleStreams(False)
        self.playingChanged.emit(False)

    def _setHasMultipleStreams(self, value: bool) -> None:
        if value != self._hasMultipleStreams:
            self._hasMultipleStreams = value
            self.hasMultipleStreamsChanged.emit(value)

    def _resetSubtitleState(self) -> None:
        """Reset all subtitle state for a new video or stream switch."""
        self._userSelectedSub = False
        self._subtitleTracks = []
        self._hasSubtitles = False
        self.hasSubtitlesChanged.emit(False)
        self._subtitlesViewModel.resetItems([])
        if self._currentSubtitleIndex != 0:
            self._currentSubtitleIndex = 0
            self.currentSubtitleIndexChanged.emit(0)

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
        self._resetSubtitleState()
        self._setHasMultipleStreams(len(streams) > 1)
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
            self._resetSubtitleState()
            self.playUrlRequested.emit(self._streamUrls[index].url)
            logger.info(
                "Switched to stream %s/%s: %s",
                index,
                len(self._streamUrls),
                self._streamUrls[index].url,
            )

    @Slot(int)
    def switchSubtitle(self, index: int):
        if index == self._currentSubtitleIndex:
            return
        self._currentSubtitleIndex = index
        self._userSelectedSub = index > 0
        self.currentSubtitleIndexChanged.emit(index)
        trackId = 0 if index == 0 else self._subtitleTracks[index - 1].trackId
        logger.info(
            "switchSubtitle: index=%d, trackId=%d, model tracks=%s",
            index,
            trackId,
            [(t.trackId, t.name, t.langCode) for t in self._subtitleTracks],
        )
        self.subtitleTrackChanged.emit(trackId)

    @Slot(list)
    def updateSubtitleTracks(self, tracks: list[SubtitleModel]):
        self._subtitleTracks = tracks
        off = SubtitleModel(name="Off", trackId=0, langCode="")
        items = [off, *tracks]
        self._subtitlesViewModel.resetItems(items)
        hasChanged = (len(tracks) > 0) != self._hasSubtitles
        self._hasSubtitles = len(tracks) > 0
        if hasChanged:
            self.hasSubtitlesChanged.emit(self._hasSubtitles)
        if not self._userSelectedSub:
            self._currentSubtitleIndex = 0
            self.currentSubtitleIndexChanged.emit(0)

    @Slot(bool)
    def setPlaying(self, playing: bool):
        if playing and self._sessionStartTime is None:
            self._sessionStartTime = datetime.now(UTC)
            self._sessionChannelId = self._channelId
            logger.info("Watch session started for channel %s", self._sessionChannelId)
        self._playing = playing
        self.playingChanged.emit(playing)
