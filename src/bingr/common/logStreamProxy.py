"""stdout/stderr proxies that route console output into Python logging.

Captures everything written via ``print()`` or direct ``sys.stdout`` /
``sys.stderr`` writes — including libmpv/ffmpeg log lines emitted through
python-mpv's ``log_handler=print`` — and forwards each line to the ``bingr``
logger tree so it lands in bingr.log alongside normal application logs.

Works identically under local dev (uv run), flatpak sandboxes, and Nuitka
builds: it operates purely at the Python stream level.
"""

from __future__ import annotations

import logging
import sys

_stdoutProxy: _LogStreamProxy | None = None
_stderrProxy: _LogStreamProxy | None = None


class _LogStreamProxy:
    """Line-buffered stream wrapper that mirrors every written line to a logger."""

    def __init__(self, original, logger: logging.Logger, level: int):
        self._original = original
        self._logger = logger
        self._level = level
        self._buffer = ""
        self.encoding = getattr(original, "encoding", "utf-8")

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        try:
            return self._original.write(text)
        except Exception:
            return len(text)

    def flush(self) -> None:
        self._emit(self._buffer)
        self._buffer = ""
        try:
            self._original.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False

    def __getattr__(self, name: str):
        return getattr(self._original, name)

    def _emit(self, line: str) -> None:
        line = line.rstrip()
        if line:
            self._logger.log(self._level, "%s", line)


def installStreamProxies() -> None:
    """Wrap sys.stdout/sys.stderr so print output lands in bingr.log too.

    Must be called AFTER setupLogging() has created its handlers — those hold
    references to the real streams, so logging never recurses through the
    proxies. Idempotent: repeated calls are no-ops.
    """
    global _stdoutProxy, _stderrProxy
    if _stdoutProxy is None:
        _stdoutProxy = _LogStreamProxy(
            sys.stdout, logging.getLogger("bingr.stdout"), logging.INFO
        )
        sys.stdout = _stdoutProxy  # type: ignore[assignment]
    if _stderrProxy is None:
        _stderrProxy = _LogStreamProxy(
            sys.stderr, logging.getLogger("bingr.stderr"), logging.WARNING
        )
        sys.stderr = _stderrProxy  # type: ignore[assignment]
