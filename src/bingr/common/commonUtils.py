"""Shared, dependency-light utilities used across the application.

``normalizeUrl`` and ``trimHeap`` live here so any service or job that needs
URL-normalized keys or post-release heap trimming can reuse them instead of
duplicating the implementation.
"""

from __future__ import annotations

import ctypes as _ctypes
import logging
import os
from pathlib import Path

from PySide6.QtCore import QUrl

logger = logging.getLogger(__name__)


# ── Execution environment detection ───────────────────────────────


def isFlatpak() -> bool:
    """Detect Flatpak sandbox — checks ``/.flatpak-info`` and ``FLATPAK_ID``."""
    return Path("/.flatpak-info").exists() or bool(os.environ.get("FLATPAK_ID"))


def isNuitka() -> bool:
    """Detect Nuitka compiled binary."""
    return "__compiled__" in globals()

# glibc is the only common C library that exports ``malloc_trim``. Try every
# common library name before giving up: some distros only ship ``libc.so.6``,
# others ``libc.so``. A candidate that loads but lacks the symbol is skipped.
_libc: _ctypes.CDLL | None = None
for _libName in ("libc.so.6", "libc.so"):
    try:
        _candidate = _ctypes.CDLL(_libName)
        if not hasattr(_candidate, "malloc_trim"):
            continue
        _libc = _candidate
        break
    except OSError:
        continue


def normalizeUrl(url: str) -> str:
    """Normalize a URL for dedup keys.

    ``QUrl`` lowercases the scheme and host and keeps path case, so the
    resulting key matches HTTP semantics (case-sensitive paths, normalized
    scheme/host).
    """
    return QUrl(url).toString()


def trimHeap() -> None:
    """Ask glibc to return free heap pages to the OS.

    Call after releasing large allocations (e.g. probe result batches) so the
    process RSS reflects actual usage instead of glibc's retained arena memory.

    Tries a couple of common libc library names, logs a warning when none is
    available (non-glibc platforms), and logs any failure to call
    ``malloc_trim``. It never raises — callers can always invoke it
    unconditionally.
    """
    if _libc is None:
        logger.warning(
            "trimHeap: no libc with malloc_trim found — skipping heap trim"
        )
        return
    try:
        _libc.malloc_trim(0)
    except OSError as exc:
        logger.warning("trimHeap: malloc_trim failed: %s", exc)
