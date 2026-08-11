"""Periodic refresh job for the hero channels section.

Emits ``heroChannelsReloadRequested`` on the event bus every N minutes;
the hero view model listens and reloads its top-channels list.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

from bingr.common.eventBus import appEventBus
from bingr.services.settingsService import SettingsService

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_MINUTES = 1


class HeroChannelsPeriodicRefreshJob(QObject):
    """Scheduler that emits heroChannelsReloadRequested every interval."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # settings = SettingsService(self)
        # intervalMinutes = settings.get("bingr/heroRefreshIntervalMin", DEFAULT_INTERVAL_MINUTES)
        intervalMinutes = 2
        self._timer = QTimer(self)
        self._timer.setInterval(int(intervalMinutes) * 60 * 1000)
        self._timer.timeout.connect(self._emitRefresh)
        self._timer.start()
        logger.info(
            "HeroChannelsPeriodicRefreshJob scheduled to run every %s minute(s)",
            intervalMinutes,
        )

    def _emitRefresh(self) -> None:
        logger.info("HeroChannelsPeriodicRefreshJob triggered")
        appEventBus.heroChannelsReloadRequested.emit()

    def stop(self) -> None:
        """Gracefully stop the timer so no more events are emitted."""
        self._timer.stop()
        logger.info("HeroChannelsPeriodicRefreshJob stopped")
