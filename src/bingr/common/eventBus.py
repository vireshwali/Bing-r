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
    # Add more signals here as needed

    def __init__(self) -> None:
        super().__init__()


# Eager singleton at module level
appEventBus = EventBus()
