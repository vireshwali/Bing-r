"""Real-endpoint integration tests for HttpProbeService — no mocks.

Probes well-known public HLS endpoints through a real QNetworkAccessManager.
The Qt event loop is pumped manually (``processEvents``) from the asyncio
test loop, mirroring how QtAsyncio drives it in the app.

Endpoint classes:
- GOOD: long-lived public test streams (mux.dev, Unified Streaming, Akamai).
- BAD: 404s served by those same live hosts + an RFC 6761 ``.invalid`` DNS
  failure that can never resolve.
"""

import asyncio
from typing import ClassVar

import pytest
from PySide6.QtCore import QCoreApplication

from bingr.services.httpProbeService import HttpProbeService

pytestmark = pytest.mark.external_http

GOOD_URLS = {
    "unified-tos": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
    "mux-x36xhzz": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    "mux-pts-shift": "https://test-streams.mux.dev/pts_shift/master.m3u8",
    "akamai-live": "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8",
}

BAD_URLS = {
    "mux-missing": "https://test-streams.mux.dev/no-such-file-bingr-test.m3u8",
    "unified-missing": "https://demo.unified-streaming.com/no-such-path-bingr-test.m3u8",
    "dns-invalid": "http://nonexistent.invalid/stream.m3u8",
}


@pytest.fixture(scope="session")
def qApp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def service(qApp):
    svc = HttpProbeService(timeoutSeconds=15.0, concurrency=4)
    yield svc
    svc.reset()


async def pumpUntil(predicate, timeoutSeconds=30.0):
    """Pump the Qt event loop until predicate() is true or timeout."""
    app = QCoreApplication.instance()
    assert app is not None, "QCoreApplication fixture must be active"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeoutSeconds
    while not predicate():
        if loop.time() >= deadline:
            pytest.fail("Timed out waiting for Qt network events")
        app.processEvents()
        await asyncio.sleep(0.01)


async def runProbe(service, urls):
    task = asyncio.create_task(service.probeBatch(urls))
    await pumpUntil(task.done)
    return await task


class TestRealEndpoints:
    async def testGoodUrlsReachable(self, service):
        results = await runProbe(service, GOOD_URLS)
        unreachable = [label for label, ok in results.items() if not ok]
        assert not unreachable, f"Expected reachable but failed: {unreachable}"

    async def testBadUrlsUnreachable(self, service):
        results = await runProbe(service, BAD_URLS)
        wronglyReachable = [label for label, ok in results.items() if ok]
        assert not wronglyReachable, f"Expected unreachable but succeeded: {wronglyReachable}"

    async def testMixedBatchClassifiesBoth(self, service):
        urls = {"good": GOOD_URLS["mux-x36xhzz"], "bad": BAD_URLS["dns-invalid"]}
        results = await runProbe(service, urls)
        assert results == {"good": True, "bad": False}

    async def testDedupFiresSingleRequest(self, service):
        url = GOOD_URLS["mux-x36xhzz"]
        variant = url.replace("https://", "HTTPS://").replace("test-streams.mux.dev", "TEST-STREAMS.MUX.DEV")
        urls = {"plain": url, "shouty": variant}

        origGet = service._mgr.get
        callCount = {"n": 0}

        def countingGet(request):
            callCount["n"] += 1
            return origGet(request)

        service._mgr.get = countingGet
        results = await runProbe(service, urls)

        assert results == {"plain": True, "shouty": True}
        assert callCount["n"] == 1, f"Expected 1 deduplicated request, got {callCount['n']}"

    async def testConcurrentBatchesIndependent(self, service):
        tGood = asyncio.create_task(runProbe(service, {"g": GOOD_URLS["mux-pts-shift"]}))
        tBad = asyncio.create_task(runProbe(service, {"b": BAD_URLS["dns-invalid"]}))
        goodResults, badResults = await asyncio.gather(tGood, tBad)
        assert goodResults == {"g": True}
        assert badResults == {"b": False}

    async def testResetBetweenBatchesKeepsWorking(self, service):
        first = await runProbe(service, {"a": GOOD_URLS["unified-tos"]})
        assert first == {"a": True}

        service.reset()

        second = await runProbe(service, {"b": BAD_URLS["mux-missing"]})
        assert second == {"b": False}

        third = await runProbe(service, {"c": GOOD_URLS["akamai-live"]})
        assert third == {"c": True}


class TestSslHandling:
    """SSL validation behavior against real self-signed endpoints (badssl.com)."""

    SSL_URLS: ClassVar[dict[str, str]] = {
        "self-signed": "https://self-signed.badssl.com/",
        "expired": "https://expired.badssl.com/",
    }

    @pytest.fixture
    def strictService(self, qApp):
        return HttpProbeService(timeoutSeconds=15.0, verifySsl=True)

    async def testInvalidCertsIgnoredByDefault(self, service):
        # verifySsl=False (default): self-signed/expired certs are judged by HTTP status.
        results = await runProbe(service, self.SSL_URLS)
        wronglyUnreachable = [label for label, ok in results.items() if not ok]
        assert not wronglyUnreachable, f"Expected reachable despite bad cert: {wronglyUnreachable}"

    async def testInvalidCertsRejectedWhenVerifying(self, strictService):
        results = await runProbe(strictService, self.SSL_URLS)
        wronglyReachable = [label for label, ok in results.items() if ok]
        assert not wronglyReachable, f"Expected unreachable with strict TLS: {wronglyReachable}"
