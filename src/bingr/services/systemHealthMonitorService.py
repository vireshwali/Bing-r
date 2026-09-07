"""Periodic system health checks — internet, disk, memory — published to the event bus."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

import httpx
from PySide6.QtCore import QObject

from bingr.common.eventBus import appEventBus

logger = logging.getLogger(__name__)

_GOOGLE_204 = "https://clients3.google.com/generate_204"

_INTERNET_CHECK_TIMEOUT = 10

_MIN_DISK_RED_GB = 5
_MIN_DISK_YELLOW_GB = 10
_MIN_RAM_GREEN_GB = 1.8
_MIN_RAM_WARNING_GB = 1.2


class SystemHealthMonitorService(QObject):
    def __init__(self, workspace: Path):
        super().__init__()
        self._workspace = workspace
        self._lastOnline: bool | None = None
        self._lastDiskStatus: str | None = None
        self._lastRamStatus: str | None = None

        appEventBus.systemHealthCheckRequested.connect(self.runAllChecksOnDemand)
        logger.debug("SystemHealthMonitorService initialized.")

    def runAllChecksOnDemand(self):
        appEventBus.statusBarProgressUpdate.emit("Checking system health...")
        asyncio.create_task(self._checkInternet())  # noqa: RUF006
        asyncio.create_task(self._checkDisk())  # noqa: RUF006
        asyncio.create_task(self._checkRam())  # noqa: RUF006

    # ── Internet ──────────────────────────────────────────────────

    async def _checkInternet(self):
        appEventBus.statusBarProgressUpdate.emit("Checking internet connection...")
        try:
            with httpx.Client(timeout=_INTERNET_CHECK_TIMEOUT) as client:
                resp = client.get(_GOOGLE_204)
                online = resp.status_code == 204
        except Exception:
            logger.warning("Internet check failed", exc_info=True)
            online = False

        if online != self._lastOnline:
            if online:
                appEventBus.statusBarInternetUpdate.emit("Internet connected and good", "success")
            else:
                appEventBus.statusBarInternetUpdate.emit("No internet connection", "error")
            self._lastOnline = online

    # ── Disk ───────────────────────────────────────────────────────

    async def _checkDisk(self):
        appEventBus.statusBarProgressUpdate.emit("Checking disk space...")
        try:
            usage = shutil.disk_usage(self._workspace)
            freeGb = usage.free / (1024**3)
        except Exception:
            logger.warning("Disk check failed", exc_info=True)
            return

        if freeGb >= _MIN_DISK_YELLOW_GB:
            status = "green"
        elif freeGb >= _MIN_DISK_RED_GB:
            status = "yellow"
        else:
            status = "red"

        if status != self._lastDiskStatus:
            if status == "green":
                appEventBus.statusBarDiskUpdate.emit("Disk space is good.", "success")
            elif status == "yellow":
                appEventBus.statusBarDiskUpdate.emit(f"Disk space is low: {freeGb:.1f}GB free", "warning")
            else:
                appEventBus.statusBarDiskUpdate.emit(f"Critically low disk space: {freeGb:.1f}GB free", "error")
            self._lastDiskStatus = status

    # ── RAM ────────────────────────────────────────────────────────

    async def _checkRam(self):
        appEventBus.statusBarProgressUpdate.emit("Checking system memory...")
        freeGb = self._getAvailableRamGb()

        if freeGb >= _MIN_RAM_GREEN_GB:
            status = "green"
        elif freeGb >= _MIN_RAM_WARNING_GB:
            status = "yellow"
        else:
            status = "red"

        if status != self._lastRamStatus:
            if status == "green":
                appEventBus.statusBarRamUpdate.emit("System memory is sufficient", "success")
            elif status == "yellow":
                appEventBus.statusBarRamUpdate.emit(f"System memory is low: {freeGb:.1f}GB free", "warning")
            else:
                appEventBus.statusBarRamUpdate.emit(f"Critical system memory: {freeGb:.1f}GB free", "error")
            self._lastRamStatus = status

    def _getAvailableRamGb(self) -> float:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / (1024**2)
        except Exception:
            logger.warning("Could not read /proc/meminfo", exc_info=True)
        return 0.0
