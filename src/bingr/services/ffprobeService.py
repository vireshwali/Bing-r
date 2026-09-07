"""Playability validation of stream URLs via ``ffprobe`` subprocesses.

HTTP reachability alone does not prove a stream plays: a master playlist can be
served while its segments 404. This service re-validates URLs by running
``ffprobe`` on each one in an OS-level ``QProcess`` subprocess (QtAsyncio does
not implement asyncio subprocess support) and reports whether the stream can be
opened.

Design notes:

- **Instance-scoped state.** Defaults (timeout, concurrency, binary path) are
  constructor parameters with sensible defaults; nothing is shared between
  instances.
- **Reentrant yet mutually exclusive.** Concurrent ``validate``/
  ``validateBatch`` calls on one instance are safe: an ``asyncio.Lock``
  serializes whole validation runs while an internal semaphore caps how many
  subprocesses run inside a single batch.
- **Replies as return values, callbacks optional.** ``validate`` returns
  ``(ok, reason)``; ``validateBatch`` mutates its ``results`` dict in place and
  can additionally report each outcome through an ``onResult`` callback.
"""

from __future__ import annotations

import asyncio
import locale
import logging
from collections.abc import Callable

from PySide6.QtCore import QProcess

logger = logging.getLogger(__name__)

# Mirrors the Chrome user-agent used by HttpProbeService so IPTV servers that
# reject non-browser UAs behave identically for HTTP and ffprobe validation.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _disconnectSignals(proc: QProcess) -> None:
    """Disconnect all signal handlers from *proc* before deletion."""
    for sig in (proc.finished, proc.errorOccurred):
        try:
            sig.disconnect()
        except (TypeError, RuntimeError):
            pass


class FfprobeService:
    """Probes stream URLs with ffprobe and reports whether they play."""

    def __init__(
        self,
        timeoutSeconds: float = 45.0,
        concurrency: int = 6,
        ffprobePath: str = "ffprobe",
        userAgent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        # Qt's QGuiApplication sets LC_ALL="" which inherits the user locale;
        # ffprobe parses timestamps with locale-dependent sscanf, so under e.g.
        # de_DE a value like "45.500000" can be misread. Force C for correct
        # probing regardless of the user's locale.
        locale.setlocale(locale.LC_NUMERIC, "C")
        self._timeoutSeconds = timeoutSeconds
        self._waitForTimeout = timeoutSeconds + 4.0  # 4 seconds more than ffprobe timeout
        self._concurrency = concurrency
        self._ffprobePath = ffprobePath
        self._userAgent = userAgent
        self._lock = asyncio.Lock()

    async def validate(
        self,
        url: str,
        onResult: Callable[[str, bool, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Probe a single URL with ffprobe.

        Returns ``(ok, reason)`` where ``reason`` is a short human-readable
        outcome.
        """
        async with self._lock:
            ok, reason = await self._probeFfprobe(url)
        if onResult is not None:
            onResult(url, ok, reason)
        return ok, reason

    async def validateBatch(
        self,
        results: dict[str, bool],
        keyToUrl: dict[str, str],
        onResult: Callable[[str, bool, str], None] | None = None,
    ) -> None:
        """Confirm HTTP-reachable URLs are actually playable with ffprobe.

        Only URLs that are currently ``True`` in ``results`` are re-validated;
        those that fail here are downgraded to ``False`` before returning.
        ``results`` is mutated in place so the caller reads the final
        reachability for every URL. ``onResult``, when given, is invoked as
        ``(key, ok, reason)`` for each probed URL.

        Each probe runs in its own OS process (via ``QProcess``), so the only
        in-process resource is bounded by the semaphore and there is no C heap
        to reclaim.
        """
        toProbe = [(key, keyToUrl[key]) for key, reachable in results.items() if reachable]
        if not toProbe:
            logger.info("ffprobe validation: no HTTP-reachable URLs to validate")
            return

        logger.info(
            "ffprobe validation starting — %d URL(s), concurrency %d",
            len(toProbe),
            self._concurrency,
        )
        async with self._lock:
            semaphore = asyncio.Semaphore(self._concurrency)

            async def validateOne(key: str, url: str) -> None:
                async with semaphore:
                    ok, reason = await self._probeFfprobe(url)
                if not ok:
                    logger.warning("FFPROBE FAIL %s — %s", url, reason)
                    results[key] = False
                if onResult is not None:
                    onResult(key, ok, reason)

            await asyncio.gather(*(validateOne(key, url) for key, url in toProbe))

    async def _probeFfprobe(self, url: str) -> tuple[bool, str]:
        """Probe ``url`` with ffprobe in a QProcess subprocess.

        Returns ``(ok, reason)``. Connects the ``finished`` / ``errorOccurred``
        signals to an ``asyncio.Future`` resolved on the Qt event loop, then
        awaits it with a timeout. The subprocess is reaped by its own exit, and
        the ``QProcess`` object is released via ``deleteLater``.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[tuple[int, str]] = loop.create_future()
        proc = QProcess()

        def _resolve(exitCode: int, errText: str) -> None:
            # QtAsyncio runs Qt and asyncio on the same thread, so resolving
            # directly avoids an extra event-loop hop that, under 6 concurrent
            # probes, can let the wait_for timeout fire before the future is
            # resolved for a process that already finished.
            if not future.done():
                future.set_result((exitCode, errText))

        def _cleanup(exitCode: int, errText: str) -> None:
            # Disconnect BEFORE deleteLater so a late signal (e.g. finished
            # after kill on the timeout path) cannot fire against a deleted
            # C++ wrapper. Idempotent if both signals already fired.
            _disconnectSignals(proc)
            proc.deleteLater()
            _resolve(exitCode, errText)

        def _onFinished(exitCode: int, exitStatus: QProcess.ExitStatus) -> None:
            errText = bytes(proc.readAllStandardError()).decode(errors="replace").strip()[:120]
            _cleanup(exitCode, errText)

        def _onError(error: QProcess.ProcessError) -> None:
            _cleanup(-1, proc.errorString())

        proc.finished.connect(_onFinished)
        proc.errorOccurred.connect(_onError)
        proc.setProgram(self._ffprobePath)
        proc.setArguments(
            [
                "-user_agent",
                self._userAgent,
                "-v",
                "error",
                "-extension_picky",
                "false",
                "-show_format",
                "-show_streams",
                "-rw_timeout",
                str(int(self._timeoutSeconds * 1_000_000)),
                url,
            ]
        )

        try:
            proc.start()
        except Exception as exc:
            _disconnectSignals(proc)
            proc.deleteLater()
            return False, f"ffprobe could not start: {exc}"

        try:
            exitCode, errText = await asyncio.wait_for(future, timeout=self._waitForTimeout)
        except TimeoutError:
            proc.kill()
            _cleanup(-1, "ffprobe timed out")
            return False, "ffprobe timed out"
        if exitCode == 0:
            return True, "ok"
        return False, errText or f"ffprobe exited {exitCode}"
