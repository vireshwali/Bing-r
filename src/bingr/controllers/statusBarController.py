"""Status_Bar_Controller — message queue + DB count refresh for UI status bar."""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtQml import QmlElement, QmlSingleton
from sqlalchemy import func, select

from bingr.common.eventBus import appEventBus
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

_QUEUE_DRAIN_INTERVAL_MS = 400
_COUNT_REFRESH_INTERVAL_MS = 6_000
_IDLE_MSG = "Idle."


@QmlElement
@QmlSingleton
class StatusBarController(QObject):
    progressMsg = Signal(str, arguments=["msg"])
    internetStatus = Signal(str, str, arguments=["msg", "msgType"])
    diskStatus = Signal(str, str, arguments=["msg", "msgType"])
    ramStatus = Signal(str, str, arguments=["msg", "msgType"])

    channelsMsg = Signal(str, arguments=["msg"])
    favouritesMsg = Signal(str, arguments=["msg"])
    playlistsMsg = Signal(str, arguments=["msg"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: deque[tuple[str, tuple]] = deque()
        self._msgQueueDrainTimer = QTimer(self)
        self._msgQueueDrainTimer.setInterval(_QUEUE_DRAIN_INTERVAL_MS)
        self._msgQueueDrainTimer.timeout.connect(self._drain)

        self._countTimer = QTimer(self)
        self._countTimer.setInterval(_COUNT_REFRESH_INTERVAL_MS)
        self._countTimer.timeout.connect(self.refreshCounts)

        self._refreshing = False

        appEventBus.statusBarProgressUpdate.connect(self._onProgressUpdate)
        appEventBus.statusBarInternetUpdate.connect(self._onInternetUpdate)
        appEventBus.statusBarDiskUpdate.connect(self._onDiskUpdate)
        appEventBus.statusBarRamUpdate.connect(self._onRamUpdate)

    # ── Event bus handlers ────────────────────────────────────────

    def _onProgressUpdate(self, msg: str):
        self._enqueue("progressMsg", msg)

    def _onInternetUpdate(self, msg: str, msgType: str):
        self._enqueue("internetStatus", msg, msgType)

    def _onDiskUpdate(self, msg: str, msgType: str):
        self._enqueue("diskStatus", msg, msgType)

    def _onRamUpdate(self, msg: str, msgType: str):
        self._enqueue("ramStatus", msg, msgType)

    # ── Queue ─────────────────────────────────────────────────────

    def _enqueue(self, target: str, *args):
        if not args or not args[0]:
            return
        if len(self._queue) >= 100:
            self._queue.popleft()
        self._queue.append((target, args))
        if not self._msgQueueDrainTimer.isActive():
            self._msgQueueDrainTimer.start()

    def _drain(self):
        if not self._queue:
            self._msgQueueDrainTimer.stop()
            return
        target, args = self._queue.popleft()
        getattr(self, target).emit(*args)
        if not self._queue:
            self._msgQueueDrainTimer.stop()
            QTimer.singleShot(_QUEUE_DRAIN_INTERVAL_MS, self._emitIdle)

    def _emitIdle(self):
        if not self._queue and not self._msgQueueDrainTimer.isActive():
            self.progressMsg.emit(_IDLE_MSG)

    def clearQueue(self):
        """Clear all queued messages and stop the drain timer."""
        self._queue.clear()
        self._msgQueueDrainTimer.stop()
        self.progressMsg.emit(_IDLE_MSG)

    # ── Publish ───────────────────────────────────────────────────

    def publishProgress(self, msg: str):
        self._enqueue("progressMsg", msg)

    def publishInternetStatus(self, msg: str, msgType: str = "info"):
        self._enqueue("internetStatus", msg, msgType)

    def publishDiskStatus(self, msg: str, msgType: str = "info"):
        self._enqueue("diskStatus", msg, msgType)

    def publishRamStatus(self, msg: str, msgType: str = "info"):
        self._enqueue("ramStatus", msg, msgType)

    # ── DB count refresh ──────────────────────────────────────────

    def refreshCounts(self):
        if self._refreshing:
            return
        self._refreshing = True
        asyncio.create_task(self._doRefresh())  # noqa: RUF006

    async def _doRefresh(self):
        try:
            sm = DatabaseManager.get_sessionmaker()
            async with sm() as session:
                stmt = select(func.count()).select_from(Channel)
                count = (await session.execute(stmt)).scalar() or 0
                self.channelsMsg.emit(f"Channels: {count}")
        except Exception as e:
            logger.warning("Channel count refresh failed: %s", e)
            self.channelsMsg.emit("Channels: 0")
        finally:
            self._refreshing = False

        self.favouritesMsg.emit("Favourites: 0")
        self.playlistsMsg.emit("Playlists: 0")

    def startCountTimer(self):
        if not self._countTimer.isActive():
            self._countTimer.start()
