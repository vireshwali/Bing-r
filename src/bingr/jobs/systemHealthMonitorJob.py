"""Periodic health monitor job — triggers health checks via the event bus.

Emits ``systemHealthCheckRequested`` on the event bus every N seconds;
SystemHealthMonitorService subscribes and runs internet/disk/ram checks.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

from bingr.common.eventBus import appEventBus

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 60


class SystemHealthMonitorJob(QObject):
    """Scheduler that emits systemHealthCheckRequested every interval."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(_DEFAULT_INTERVAL_SECONDS * 1000)
        self._timer.timeout.connect(self._emit)
        self._timer.start()
        logger.info(
            "SystemHealthMonitorJob scheduled to run every %s second(s)",
            _DEFAULT_INTERVAL_SECONDS,
        )

    def _emit(self) -> None:
        appEventBus.systemHealthCheckRequested.emit()

    def stop(self) -> None:
        """Gracefully stop the timer so no more events are emitted."""
        self._timer.stop()
        logger.info("SystemHealthMonitorJob stopped")
