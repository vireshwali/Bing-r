"""Unit tests for HttpProbeService — Qt reply handling with a mocked QNAM.

The QNAM factory is patched out entirely; Qt signal delivery is simulated by
calling ``_onReply`` directly, so these tests exercise the pure logic:
status classification, dedup keying, timeout release, takeover and reset.
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest

from bingr.common.commonUtils import normalizeUrl
from bingr.services.httpProbeService import HttpProbeService


def fakeReply(mocker, url, statusCode=None, error=None, errorString=""):
    reply = mocker.MagicMock()
    reply.request.return_value.url.return_value.toString.return_value = url
    reply.error.return_value = error if error is not None else QNetworkReply.NetworkError.NoError
    reply.attribute.return_value = statusCode
    reply.errorString.return_value = errorString
    return reply


class HttpProbeTestBase:
    @pytest.fixture
    def factoryPatch(self, mocker):
        return mocker.patch("bingr.services.httpProbeService.AppNetworkAccessManagerFactory")

    @pytest.fixture
    def mockMgr(self, factoryPatch):
        mgr = MagicMock()
        factoryPatch.return_value.create.return_value = mgr
        return mgr

    @pytest.fixture
    def service(self, mockMgr):
        return HttpProbeService(timeoutSeconds=2.0, concurrency=3)

    async def _settle(self, service, timeoutSteps=200):
        """Advance the loop until _probeOne has registered its pending future."""
        for _ in range(timeoutSteps):
            if service._pending:
                return True
            await asyncio.sleep(0)
        return False


class TestConstruction(HttpProbeTestBase):
    def testManagerConfiguredFromDefaults(self, service, mockMgr):
        mockMgr.setRedirectPolicy.assert_called_once_with(
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
        )
        mockMgr.setTransferTimeout.assert_called_once_with(2000)
        mockMgr.finished.connect.assert_called_once_with(service._onReply)
        mockMgr.sslErrors.connect.assert_called_once_with(service._onSslErrors)

    def testNoRedirectsPolicy(self, mockMgr):
        HttpProbeService(followRedirects=False)
        mockMgr.setRedirectPolicy.assert_called_with(QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)

    def testVerifySslSkipsSslHook(self, mockMgr):
        HttpProbeService(verifySsl=True)
        mockMgr.sslErrors.connect.assert_not_called()


class TestProbeSingle(HttpProbeTestBase):
    async def testSuccessResolvesReachable(self, service, mockMgr, mocker):
        url = "https://example.com/live.m3u8"
        reply = fakeReply(mocker, url, statusCode=200)

        task = asyncio.create_task(service.probe(url))
        assert await self._settle(service)
        mockMgr.get.assert_called_once()

        service._onReply(reply)
        reachable, reason = await asyncio.wait_for(task, timeout=1.0)

        assert reachable is True
        assert reason == "ok"
        assert service._pending == {}
        reply.close.assert_called_once()
        reply.deleteLater.assert_called_once()

    async def testHttpErrorStatusUnreachable(self, service, mocker):
        url = "https://example.com/missing.m3u8"
        reply = fakeReply(mocker, url, statusCode=404)

        task = asyncio.create_task(service.probe(url))
        assert await self._settle(service)
        service._onReply(reply)

        reachable, reason = await asyncio.wait_for(task, timeout=1.0)
        assert reachable is False
        assert reason == "unreachable"

    async def testNetworkErrorUnreachable(self, service, mocker):
        url = "https://example.com/refused.m3u8"
        reply = fakeReply(
            mocker,
            url,
            statusCode=None,
            error=QNetworkReply.NetworkError.ConnectionRefusedError,
            errorString="Connection refused",
        )

        task = asyncio.create_task(service.probe(url))
        assert await self._settle(service)
        service._onReply(reply)

        reachable, _reason = await asyncio.wait_for(task, timeout=1.0)
        assert reachable is False

    async def testTimeoutReleasesPending(self, service):
        task = asyncio.create_task(service.probe("https://slow.example.com/a.m3u8"))
        assert await self._settle(service)

        # Never deliver the reply — the internal wait_for must time out.
        reachable, reason = await asyncio.wait_for(task, timeout=3.0)
        assert reachable is False
        assert reason == "unreachable"
        assert service._pending == {}

    async def testGetFailureReturnsUnreachable(self, service, mockMgr):
        mockMgr.get.side_effect = RuntimeError("boom")

        reachable, reason = await service.probe("https://example.com/x.m3u8")
        assert reachable is False
        assert reason == "unreachable"
        assert service._pending == {}

    async def testOnResultCallbackInvoked(self, service, mocker):
        calls = []
        url = "https://example.com/cb.m3u8"
        reply = fakeReply(mocker, url, statusCode=200)

        task = asyncio.create_task(service.probe(url, onResult=lambda label, ok: calls.append((label, ok))))
        assert await self._settle(service)
        service._onReply(reply)
        await asyncio.wait_for(task, timeout=1.0)

        assert calls == [(normalizeUrl(url), True)]


class TestBatching(HttpProbeTestBase):
    async def testEmptyBatchReturnsEmpty(self, service):
        assert await service.probeBatch({}) == {}

    async def testDedupSharesOneRequest(self, service, mockMgr, mocker):
        urls = {
            "upper": "https://Host.example/P.m3u8",
            "lower": "https://host.example/P.m3u8",
        }
        assert normalizeUrl(urls["upper"]) == normalizeUrl(urls["lower"])

        reply = fakeReply(mocker, normalizeUrl(urls["lower"]), statusCode=200)
        task = asyncio.create_task(service.probeBatch(urls))
        for _ in range(200):
            if mockMgr.get.call_count == 1:
                break
            await asyncio.sleep(0)

        service._onReply(reply)
        results = await asyncio.wait_for(task, timeout=1.0)

        assert results == {"upper": True, "lower": True}
        assert mockMgr.get.call_count == 1

    async def testMixedBatchMapsEachKey(self, service, mocker):
        good = "https://good.example.com/a.m3u8"
        bad = "https://bad.example.com/b.m3u8"

        task = asyncio.create_task(service.probeBatch({"g": good, "b": bad}))
        for _ in range(200):
            if len(service._pending) == 2:
                break
            await asyncio.sleep(0)
        assert len(service._pending) == 2

        service._onReply(fakeReply(mocker, bad, statusCode=500))
        service._onReply(fakeReply(mocker, good, statusCode=200))

        results = await asyncio.wait_for(task, timeout=1.0)
        assert results == {"g": True, "b": False}

    async def testConcurrentSameUrlTakeover(self, service, mockMgr, mocker):
        url = "https://race.example.com/live.m3u8"
        key = normalizeUrl(url)

        t1 = asyncio.create_task(service._probeOne(url, key, ["a"], None))
        assert await self._settle(service)
        firstFuture = service._pending[key]

        t2 = asyncio.create_task(service._probeOne(url, key, ["b"], None))
        for _ in range(200):
            if service._pending.get(key) is not firstFuture:
                break
            await asyncio.sleep(0)

        k1, r1 = await t1
        assert (k1, r1) == (key, False)  # earlier call resolved as unreachable

        service._onReply(fakeReply(mocker, url, statusCode=200))
        k2, r2 = await t2
        assert (k2, r2) == (key, True)
        assert mockMgr.get.call_count == 2


class TestEdgePaths(HttpProbeTestBase):
    def testOnSslErrorsIgnoresEveryReply(self, service):
        reply = MagicMock()
        reply.request.return_value.url.return_value.toString.return_value = "https://self-signed.example/"

        service._onSslErrors(reply, ["cert1", "cert2"])

        reply.ignoreSslErrors.assert_called_once()

    def testBodySnippetDecodesChunk(self, service):
        reply = MagicMock()
        reply.read.return_value = b"<html>404 Not Found</html>"

        assert service._bodySnippet(reply) == "<html>404 Not Found</html>"
        reply.read.assert_called_once_with(service._BODY_SNIPPET_MAX)

    def testBodySnippetReadFailureReturnsEmpty(self, service):
        reply = MagicMock()
        reply.read.side_effect = RuntimeError("reply already closed")

        assert service._bodySnippet(reply) == ""

    async def testReplyHandlerExceptionTreatedUnreachable(self, service, mocker):
        url = "https://example.com/explode.m3u8"
        reply = fakeReply(mocker, url, statusCode=200)
        # _onReply wraps attribute()/status handling in try/except — make that raise.
        reply.attribute.side_effect = RuntimeError("boom")

        task = asyncio.create_task(service.probe(url))
        assert await self._settle(service)
        service._onReply(reply)

        reachable, reason = await asyncio.wait_for(task, timeout=1.0)
        assert reachable is False
        assert reason == "unreachable"
        assert service._pending == {}
        reply.close.assert_called_once()
        reply.deleteLater.assert_called_once()

    async def testResetToleratesDisconnectErrors(self, service, mockMgr, factoryPatch):
        old = service._mgr
        old.finished.disconnect.side_effect = RuntimeError("already disconnected")
        old.sslErrors.disconnect.side_effect = TypeError("no such handler")
        freshMgr = MagicMock()
        factoryPatch.return_value.create.return_value = freshMgr

        service.reset()

        assert service._mgr is freshMgr
        assert service._pending == {}
        old.deleteLater.assert_called_once()
        freshMgr.setTransferTimeout.assert_called_once_with(2000)


class TestReset(HttpProbeTestBase):
    async def testResetDiscardsOldManagerAndPending(self, service, mockMgr, factoryPatch, mocker):
        service._pending[normalizeUrl("https://stale.example.com/s.m3u8")] = asyncio.get_running_loop().create_future()
        old = service._mgr

        freshMgr = MagicMock()
        factoryPatch.return_value.create.return_value = freshMgr
        service.reset()

        old.finished.disconnect.assert_called_once_with(service._onReply)
        old.deleteLater.assert_called_once()
        assert service._pending == {}
        assert service._mgr is freshMgr
        assert freshMgr.setTransferTimeout.call_args[0][0] == 2000

        # Fresh manager still probes fine.
        reply = fakeReply(mocker, "https://fresh.example.com/f.m3u8", statusCode=200)
        task = asyncio.create_task(service.probe("https://fresh.example.com/f.m3u8"))
        assert await self._settle(service)
        service._onReply(reply)
        assert await asyncio.wait_for(task, timeout=1.0) == (True, "ok")
