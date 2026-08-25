from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """Central application event bus — singleton QObject for Python-side pub/sub.

    Used by controllers/services to emit events and by ViewModels to subscribe.
    All signals use camelCase naming. Instantiate once at module import (eager).

    Example:
        from bingr.common.eventBus import appEventBus
        from bingr.common.eventTypes import ReloadChannelsDataEvent

        # Publisher
        appEventBus.reloadChannelsData.emit(ReloadChannelsDataEvent(True))

        # Subscriber (in __init__)
        appEventBus.reloadChannelsData.connect(self.onReloadChannelsGrid)

        @Slot(object)
        def onReloadChannelsData(self, event: ReloadChannelsDataEvent):
            if event.doReload:
                self.fetchMore()
    """

    reloadChannelsData = Signal(object)
    toggleFavoriteRequested = Signal(int)
    favoriteToggled = Signal(int, bool)
    heroChannelsReloadRequested = Signal()
    reachabilityCheckRequested = Signal(object)

    # Emitted by SystemHealthMonitorJob every 10s to trigger health checks.
    systemHealthCheckRequested = Signal()

    # Status bar event bus signals — emitted by services, consumed by
    # StatusBarController which queues them and drains to QML in FIFO order.

    # Emitted when a progress/status text message arrives (e.g. "Loading channels...").
    statusBarProgressUpdate = Signal(str)

    # Emitted when internet connectivity status changes.
    # msg: human-readable text, msgType: "success"|"warning"|"error"
    statusBarInternetUpdate = Signal(str, str)

    # Emitted when disk space status changes.
    # msg: human-readable text, msgType: "success"|"warning"|"error"
    statusBarDiskUpdate = Signal(str, str)

    # Emitted when RAM status changes.
    # msg: human-readable text, msgType: "success"|"warning"|"error"
    statusBarRamUpdate = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()


# Eager singleton at module level
appEventBus = EventBus()
