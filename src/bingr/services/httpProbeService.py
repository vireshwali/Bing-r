"""Generic HTTP(S) reachability probing built on Qt's ``QNetworkAccessManager``.

``QNetworkAccessManager`` is the only HTTP stack that works under QtAsyncio,
which does not implement the Level 2 asyncio networking API. This service wraps
it in an async-friendly interface: ``probe`` for a single URL and ``probeBatch``
for many at once.

Design notes:

- **Instance-scoped manager.** Every ``HttpProbeService`` owns its own
  ``QNetworkAccessManager`` and its own defaults; nothing is shared between
  instances and nothing is configured per caller through class state.
- **Defaults overridable at construction.** Timeout, concurrency, user agent,
  redirect and TLS handling are constructor parameters with sensible defaults.
- **Self-contained, lock-free calls.** ``probe`` and ``probeBatch`` are fully
  reentrant: every call keeps its dedup maps and results as coroutine-local
  state, so concurrent calls never pollute each other. The single shared
  instance attribute is ``_pending`` — a plain request-URL → future rendezvous
  dict that Qt signal handlers use to hand replies back to the right awaiter.
  It needs no lock: asyncio is single-threaded, dict operations are atomic, and
  Qt's event loop runs on the same thread. QNAM handles concurrent in-flight
  requests natively. If two concurrent calls ever target the same URL, the
  later one resolves the earlier in-flight future as unreachable so neither
  hangs.
- **Replies as return values, callbacks optional.** The default API returns
  results directly (``{key: reachable}`` for a batch, ``(reachable, reason)``
  for a single URL). Callers that want to stream results as they arrive can
  pass an ``onResult`` callback.
- **Caller keys, URL dedup.** ``probeBatch`` accepts any caller-chosen labels
  as keys and returns results under those same labels. Internally URLs are
  deduplicated by ``normalizeUrl`` key, so two labels pointing at the same
  (normalized) URL share a single probe and both receive the same result.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest

from bingr.common.appNetworkFactory import AppNetworkAccessManagerFactory
from bingr.common.commonUtils import normalizeUrl

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = (
    b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class HttpProbeService:
    """Probes URLs with a single HTTP GET and reports reachability.

    A URL counts as reachable when the request completes without a network
    error and the HTTP status is ``200 <= status < 400`` (redirects are
    followed automatically). SSL errors are ignored by default because IPTV
    servers commonly use self-signed certificates; a reachability probe judges
    a URL by its HTTP status, not its certificate.
    """

    _BODY_SNIPPET_MAX = 100

    def __init__(
        self,
        timeoutSeconds: float = 30.0,
        concurrency: int = 25,
        userAgent: bytes | None = None,
        followRedirects: bool = True,
        verifySsl: bool = False,
    ) -> None:
        self._timeoutSeconds = timeoutSeconds
        self._concurrency = concurrency
        self._userAgent = userAgent or _DEFAULT_USER_AGENT
        self._followRedirects = followRedirects
        self._verifySsl = verifySsl

        # Instance-scoped manager from the shared factory (no cache — bare
        # QNAM keeps memory and disk I/O out of the probing path).
        self._newManager()

        # The only instance-level mutable state: normalized request URL →
        # in-flight future. Written by _probeOne, popped by the reply handler.
        self._pending: dict[str, asyncio.Future] = {}

    def _newManager(self) -> None:
        """Create a fresh QNAM with this service's defaults.

        Old manager (and its DNS/SSL/keep-alive caches) must be destroyed by
        the caller via ``reset()`` before calling this.
        """
        self._mgr = AppNetworkAccessManagerFactory().create(None)
        self._mgr.setRedirectPolicy(
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
            if self._followRedirects
            else QNetworkRequest.RedirectPolicy.ManualRedirectPolicy
        )
        self._mgr.setTransferTimeout(int(self._timeoutSeconds * 1000))
        self._mgr.finished.connect(self._onReply)
        if not self._verifySsl:
            self._mgr.sslErrors.connect(self._onSslErrors)

    def reset(self) -> None:
        """Discard the current QNAM and start a fresh one.

        A long-running QNAM accumulates internal state (DNS cache, SSL session
        cache, keep-alive connection pool) that survives individual replies.
        Recreating it between probe batches releases that retained memory.
        Must be called only when no requests are in flight.
        """
        old = self._mgr
        if old is not None:
            try:
                old.finished.disconnect(self._onReply)
            except (TypeError, RuntimeError):
                pass
            try:
                old.sslErrors.disconnect(self._onSslErrors)
            except (TypeError, RuntimeError):
                pass
            old.deleteLater()
        self._pending.clear()
        self._newManager()

    async def probe(
        self,
        url: str,
        onResult: Callable[[str, bool], None] | None = None,
    ) -> tuple[bool, str]:
        """Probe a single URL.

        Returns ``(reachable, reason)`` where ``reason`` is a short
        human-readable outcome.
        """
        key = normalizeUrl(url)
        results = await self.probeBatch({key: url}, onResult=onResult)
        reachable = results.get(key, False)
        return reachable, "ok" if reachable else "unreachable"

    async def probeBatch(
        self,
        urls: dict[str, str],
        onResult: Callable[[str, bool], None] | None = None,
    ) -> dict[str, bool]:
        """Probe all ``{key: url}`` pairs and return ``{key: reachable}``.

        Keys are caller-chosen labels; results are returned under the same
        labels. URLs are deduplicated by ``normalizeUrl`` key, so a URL that
        appears twice (in whatever form) is probed exactly once and every label
        mapping to it receives the shared outcome.

        Requests are fired in bounded sub-batches of ``concurrency`` to avoid
        file descriptor exhaustion on large playlists. ``onResult``, when
        given, is invoked as ``(label, reachable)`` as each probe resolves so
        callers can stream results without waiting for the whole batch.

        Calls are self-contained and lock-free: concurrent ``probe``/
        ``probeBatch`` calls on the same instance are safe and never share
        per-batch state.
        """
        if not urls:
            return {}

        # Group caller labels by normalized request URL so each URL is probed
        # exactly once; the reply handler resolves by this same key.
        urlByRequestKey: dict[str, str] = {}
        callerKeysByRequestKey: dict[str, list[str]] = {}
        for label, url in urls.items():
            requestKey = normalizeUrl(url)
            urlByRequestKey.setdefault(requestKey, url)
            callerKeysByRequestKey.setdefault(requestKey, []).append(label)

        queue = [(urlByRequestKey[key], key) for key in urlByRequestKey]
        totalUrls = len(queue)
        if totalUrls == 0:
            return {}

        startAt = time.monotonic()
        logger.info("HTTP probe starting batch of %d unique URL(s)", totalUrls)

        results: dict[str, bool] = {}
        while queue:
            size = min(self._concurrency, len(queue))
            batch = queue[:size]
            del queue[:size]

            tasks = [
                asyncio.ensure_future(self._probeOne(url, requestKey, callerKeysByRequestKey[requestKey], onResult))
                for url, requestKey in batch
            ]
            if tasks:
                for requestKey, reachable in await asyncio.gather(*tasks):
                    results[requestKey] = reachable

        elapsed = time.monotonic() - startAt
        reachableCount = sum(1 for reachable in results.values() if reachable)
        logger.info(
            "HTTP probe batch complete — %d/%d reachable in %.1fs",
            reachableCount,
            totalUrls,
            elapsed,
        )

        return {label: results[requestKey] for requestKey, labels in callerKeysByRequestKey.items() for label in labels}

    async def _probeOne(
        self,
        url: str,
        requestKey: str,
        labels: list[str],
        onResult: Callable[[str, bool], None] | None,
    ) -> tuple[str, bool]:
        """Fire one probe and wait for its reply, releasing it on timeout.

        Returns ``(requestKey, reachable)``. ``onResult``, when given, is
        invoked with each label for this URL as soon as the outcome is known.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        # If a concurrent call is already probing this exact URL, resolve its
        # in-flight future as unreachable so it never hangs, then take over.
        existing = self._pending.get(requestKey)
        if existing is not None and not existing.done():
            existing.set_result(False)
        self._pending[requestKey] = future

        try:
            self._mgr.get(self._buildRequest(url))
        except Exception:
            self._pending.pop(requestKey, None)
            logger.exception("HTTP probe GET %s — failed to start", url)
            reachable = False
        else:
            try:
                reachable = await asyncio.wait_for(future, timeout=self._timeoutSeconds)
            except TimeoutError:
                self._pending.pop(requestKey, None)
                logger.warning(
                    "Probe failed for %s — timed out after %.0fs",
                    url,
                    self._timeoutSeconds,
                )
                reachable = False

        if onResult is not None:
            for label in labels:
                onResult(label, reachable)
        return requestKey, reachable

    def _buildRequest(self, url: str) -> QNetworkRequest:
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", self._userAgent)
        req.setRawHeader(b"Accept", b"*/*")
        return req

    def _bodySnippet(self, reply: QNetworkReply) -> str:
        """Return a truncated UTF-8 body for failure logs ('' on failure).

        Reads only ``_BODY_SNIPPET_MAX`` bytes instead of draining the whole
        response into memory (HLS playlists can be large) — the remaining body
        is dropped when ``close()`` releases the reply's read buffer.
        """
        try:
            chunk = bytes(reply.read(self._BODY_SNIPPET_MAX))
        except Exception:
            return ""
        return chunk.decode("utf-8", errors="replace")

    def _onSslErrors(self, reply: QNetworkReply, sslErrors: object) -> None:
        # IPTV stream servers frequently use self-signed/invalid certs; for a
        # reachability probe we proceed so the URL is judged by its HTTP status.
        logger.debug(
            "HTTP probe ignoring %d SSL error(s) for %s",
            len(sslErrors),  # type: ignore[arg-type]
            reply.request().url().toString(),
        )
        reply.ignoreSslErrors()

    def _onReply(self, reply: QNetworkReply) -> None:
        requestKey = normalizeUrl(reply.request().url().toString())
        error = reply.error()
        try:
            statusAttr = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            statusCode = int(statusAttr) if statusAttr is not None else None
            if error == QNetworkReply.NetworkError.NoError:
                reachable = statusCode is not None and 200 <= statusCode < 400
                if not reachable:
                    logger.warning(
                        "Probe failed for %s — HTTP %s | body: %s",
                        requestKey,
                        statusCode,
                        self._bodySnippet(reply),
                    )
            else:
                reachable = False
                statusPart = f" (HTTP {statusCode})" if statusCode is not None else ""
                logger.warning("Probe failed for %s — %s%s", requestKey, reply.errorString(), statusPart)
        except Exception:
            reachable = False
            logger.exception("HTTP probe GET %s — unexpected error", requestKey)
        finally:
            # close() immediately releases the reply's body buffer so large
            # HLS responses don't linger until the queued deleteLater fires on
            # the next event-loop pass.
            reply.close()
            reply.deleteLater()

        # Hand the outcome to whichever awaiter owns this URL; a no-op if the
        # slot was already released by a timeout or taken over by a newer call.
        future = self._pending.pop(requestKey, None)
        if future is not None and not future.done():
            future.set_result(reachable)
