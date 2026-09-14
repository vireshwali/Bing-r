"""Periodic memory trim job — runs gc.collect() + malloc_trim to reclaim memory.

Emits no signals; performs garbage collection and heap trimming on a timer to
keep RSS predictable after large imports or cache-heavy operations.
"""

from __future__ import annotations

import gc
import logging

from PySide6.QtCore import QObject, QTimer

from bingr.common.commonUtils import trimHeap

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 120


def _read_rss_kb() -> int:
    """Read current RSS from /proc/self/status (VmRSS in kB)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0


def _read_vm_size_kb() -> int:
    """Read virtual memory size from /proc/self/status (VmSize in kB)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmSize:"):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0


class MemoryTrimJob(QObject):
    """Scheduler that runs gc.collect() + malloc_trim() every N seconds."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(_INTERVAL_SECONDS * 1000)
        self._timer.timeout.connect(self._trim)
        self._timer.start()

        rss = _read_rss_kb()
        vmSize = _read_vm_size_kb()
        objCount = len(gc.get_objects())
        logger.info(
            "MemoryTrimJob scheduled every %ds — RSS %d KB, VmSize %d KB, %d Python objects",
            _INTERVAL_SECONDS,
            rss,
            vmSize,
            objCount,
        )

    def _trim(self) -> None:
        rssBefore = _read_rss_kb()
        vmBefore = _read_vm_size_kb()
        objBefore = len(gc.get_objects())

        collected = gc.collect()
        trimHeap()

        rssAfter = _read_rss_kb()
        vmAfter = _read_vm_size_kb()
        objAfter = len(gc.get_objects())

        logger.info(
            "trim: RSS %d -> %d KB (%+d), VmSize %d -> %d KB (%+d), objects %d -> %d (%+d), gc freed %d",
            rssBefore,
            rssAfter,
            rssAfter - rssBefore,
            vmBefore,
            vmAfter,
            vmAfter - vmBefore,
            objBefore,
            objAfter,
            objAfter - objBefore,
            collected,
        )

    def stop(self) -> None:
        """Gracefully stop the timer."""
        self._timer.stop()
        logger.info("MemoryTrimJob stopped")
