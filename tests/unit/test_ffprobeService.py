"""Unit tests for FfprobeService — subprocess handling with a mocked QProcess.

QProcess is patched out entirely; Qt signal delivery is simulated by invoking
the connected ``finished`` / ``errorOccurred`` handlers directly, so these
tests exercise the pure logic: argument construction, exit-code classification,
error mapping, timeout release, batch downgrading, concurrency limiting and
the instance lock that serializes whole validation runs.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bingr.services import ffprobeService as ffprobe_module
from bingr.services.ffprobeService import _DEFAULT_USER_AGENT, FfprobeService


class FfprobeTestBase:
    @pytest.fixture
    def procFactory(self, mocker):
        """Patch QProcess with a factory returning fresh mocks, tracked in a list.

        ``startError`` lets a test make ``proc.start()`` raise before the probe
        coroutine reaches it.
        """
        procs: list[MagicMock] = []
        startError = {"exc": None}

        def _factory():
            proc = mocker.MagicMock()
            proc.readAllStandardError.return_value = b""
            proc.errorString.return_value = "process error"
            if startError["exc"] is not None:
                proc.start.side_effect = startError["exc"]
            procs.append(proc)
            return proc

        mocker.patch.object(ffprobe_module, "QProcess", side_effect=_factory)
        return SimpleNamespace(procs=procs, startError=startError)

    @pytest.fixture
    def service(self, procFactory):
        return FfprobeService(timeoutSeconds=30.0, concurrency=2)

    @staticmethod
    def _fireFinished(proc, exitCode=0, stderr=b""):
        """Simulate the ``finished`` Qt signal on a mocked QProcess."""
        proc.readAllStandardError.return_value = stderr
        handler = proc.finished.connect.call_args.args[0]
        handler(exitCode, 0)  # exitStatus is unused by the handler

    @staticmethod
    def _fireError(proc, errorString="process error"):
        """Simulate the ``errorOccurred`` Qt signal on a mocked QProcess."""
        proc.errorString.return_value = errorString
        handler = proc.errorOccurred.connect.call_args.args[0]
        handler(0)  # the ProcessError value is unused by the handler

    async def _waitForProcs(self, procs, count=1, steps=200):
        """Yield to the loop until ``count`` QProcess mocks have been created."""
        for _ in range(steps):
            if len(procs) >= count:
                return True
            await asyncio.sleep(0)
        return False


class TestConstruction(FfprobeTestBase):
    def testDefaults(self):
        svc = FfprobeService()
        assert svc._timeoutSeconds == 45.0
        assert svc._waitForTimeout == 49.0
        assert svc._concurrency == 6
        assert svc._ffprobePath == "ffprobe"
        assert svc._userAgent == _DEFAULT_USER_AGENT

    def testCustomParams(self):
        svc = FfprobeService(
            timeoutSeconds=10.0,
            concurrency=3,
            ffprobePath="/usr/bin/ffprobe",
            userAgent="custom-agent/1.0",
        )
        assert svc._timeoutSeconds == 10.0
        assert svc._waitForTimeout == 14.0
        assert svc._concurrency == 3
        assert svc._ffprobePath == "/usr/bin/ffprobe"
        assert svc._userAgent == "custom-agent/1.0"

    def testForcesCNumericLocale(self, mocker):
        setlocale = mocker.patch.object(ffprobe_module.locale, "setlocale")
        FfprobeService()
        setlocale.assert_called_once_with(ffprobe_module.locale.LC_NUMERIC, "C")


class TestValidateSingle(FfprobeTestBase):
    async def testSuccessReturnsOk(self, service, procFactory):
        url = "https://example.com/live.m3u8"
        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        self._fireFinished(proc, exitCode=0)

        ok, reason = await asyncio.wait_for(task, timeout=1.0)
        assert (ok, reason) == (True, "ok")
        proc.deleteLater.assert_called_once()

    async def testLaunchesFfprobeWithExpectedArgs(self, service, procFactory):
        url = "https://example.com/live.m3u8"
        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        proc.setProgram.assert_called_once_with("ffprobe")
        proc.setArguments.assert_called_once_with(
            [
                "-user_agent",
                service._userAgent,
                "-v",
                "error",
                "-extension_picky",
                "false",
                "-show_format",
                "-show_streams",
                "-rw_timeout",
                str(30_000_000),
                url,
            ]
        )
        proc.start.assert_called_once()

        self._fireFinished(proc, exitCode=0)
        await asyncio.wait_for(task, timeout=1.0)

    async def testNonZeroExitReturnsStderr(self, service, procFactory):
        url = "https://example.com/broken.m3u8"
        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        self._fireFinished(proc, exitCode=1, stderr=b"  Connection refused\n")

        ok, reason = await asyncio.wait_for(task, timeout=1.0)
        assert ok is False
        assert reason == "Connection refused"

    async def testNonZeroExitWithoutStderrUsesExitCode(self, service, procFactory):
        url = "https://example.com/broken2.m3u8"
        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        self._fireFinished(proc, exitCode=5)

        ok, reason = await asyncio.wait_for(task, timeout=1.0)
        assert ok is False
        assert reason == "ffprobe exited 5"

    async def testErrorOccurredReturnsErrorString(self, service, procFactory):
        url = "https://example.com/crash.m3u8"
        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        self._fireError(proc, errorString="Process crashed")

        ok, reason = await asyncio.wait_for(task, timeout=1.0)
        assert ok is False
        assert reason == "Process crashed"

    async def testStartFailureReturnsError(self, service, procFactory):
        url = "https://example.com/nobinary.m3u8"
        procFactory.startError["exc"] = RuntimeError("No such file or directory")

        task = asyncio.create_task(service.validate(url))
        ok, reason = await asyncio.wait_for(task, timeout=1.0)

        assert ok is False
        assert reason == "ffprobe could not start: No such file or directory"
        procFactory.procs[0].deleteLater.assert_called_once()

    async def testTimeoutKillsProcess(self, service, procFactory):
        url = "https://slow.example.com/hang.m3u8"
        service._waitForTimeout = 0.2  # shrink the guard so the test is fast

        task = asyncio.create_task(service.validate(url))
        assert await self._waitForProcs(procFactory.procs)
        proc = procFactory.procs[0]

        # Never fire finished/error — the internal wait_for must time out.
        ok, reason = await asyncio.wait_for(task, timeout=2.0)

        assert ok is False
        assert reason == "ffprobe timed out"
        proc.kill.assert_called_once()
        proc.deleteLater.assert_called_once()

    async def testOnResultCallbackInvoked(self, service, procFactory):
        calls = []
        url = "https://example.com/cb.m3u8"
        task = asyncio.create_task(
            service.validate(url, onResult=lambda u, ok, reason: calls.append((u, ok, reason)))
        )
        assert await self._waitForProcs(procFactory.procs)

        self._fireFinished(procFactory.procs[0], exitCode=0)

        await asyncio.wait_for(task, timeout=1.0)
        assert calls == [(url, True, "ok")]


class TestValidateBatch(FfprobeTestBase):
    async def testEmptyResultsNoProbes(self, service, procFactory):
        await service.validateBatch({}, {})
        assert procFactory.procs == []

    async def testNoReachableUrlsNoProbes(self, service, procFactory):
        results = {"a": False, "b": False}
        keyToUrl = {"a": "https://a.example.com/1.m3u8", "b": "https://b.example.com/2.m3u8"}

        await service.validateBatch(results, keyToUrl)

        assert procFactory.procs == []
        assert results == {"a": False, "b": False}

    async def testOnlyReachableProbedAndFailuresDowngraded(self, service, procFactory):
        results = {"bad": False, "good": True, "also-bad": False}
        keyToUrl = {
            "bad": "https://bad.example.com/x.m3u8",
            "good": "https://good.example.com/y.m3u8",
            "also-bad": "https://also-bad.example.com/z.m3u8",
        }

        task = asyncio.create_task(service.validateBatch(results, keyToUrl))
        assert await self._waitForProcs(procFactory.procs, 1)

        # Only the reachable entry spawns a subprocess.
        assert len(procFactory.procs) == 1
        self._fireFinished(procFactory.procs[0], exitCode=1, stderr=b"Server error")

        await asyncio.wait_for(task, timeout=1.0)
        assert results == {"bad": False, "good": False, "also-bad": False}

    async def testConcurrencyCapsSimultaneousProbes(self, service, procFactory):
        results = {"a": True, "b": True, "c": True, "d": True}
        keyToUrl = {k: f"https://{k}.example.com/live.m3u8" for k in results}

        task = asyncio.create_task(service.validateBatch(results, keyToUrl))
        assert await self._waitForProcs(procFactory.procs, 2)

        # concurrency=2 caps how many subprocesses run at once; the rest wait.
        assert len(procFactory.procs) == 2
        self._fireFinished(procFactory.procs[0], exitCode=0)
        self._fireFinished(procFactory.procs[1], exitCode=0)

        assert await self._waitForProcs(procFactory.procs, 4)
        self._fireFinished(procFactory.procs[2], exitCode=0)
        self._fireFinished(procFactory.procs[3], exitCode=0)

        await asyncio.wait_for(task, timeout=2.0)
        assert results == {"a": True, "b": True, "c": True, "d": True}
        assert len(procFactory.procs) == 4

    async def testOnResultInvokedPerProbedUrl(self, service, procFactory):
        calls = []
        results = {"bad": False, "good": True}
        keyToUrl = {
            "bad": "https://bad.example.com/x.m3u8",
            "good": "https://good.example.com/y.m3u8",
        }

        task = asyncio.create_task(
            service.validateBatch(results, keyToUrl, onResult=lambda key, ok, reason: calls.append((key, ok, reason)))
        )
        assert await self._waitForProcs(procFactory.procs, 1)
        self._fireFinished(procFactory.procs[0], exitCode=1, stderr=b"nope")

        await asyncio.wait_for(task, timeout=1.0)
        assert calls == [("good", False, "nope")]
        assert results == {"bad": False, "good": False}


class TestLockSerialization(FfprobeTestBase):
    async def testConcurrentValidateCallsSerialized(self, service, procFactory):
        t1 = asyncio.create_task(service.validate("https://a.example.com/1.m3u8"))
        t2 = asyncio.create_task(service.validate("https://b.example.com/2.m3u8"))

        assert await self._waitForProcs(procFactory.procs, 1)
        await asyncio.sleep(0)
        assert len(procFactory.procs) == 1  # second call blocked on the instance lock

        self._fireFinished(procFactory.procs[0], exitCode=0)
        assert await self._waitForProcs(procFactory.procs, 2)
        self._fireFinished(procFactory.procs[1], exitCode=0)

        assert await asyncio.wait_for(t1, timeout=1.0) == (True, "ok")
        assert await asyncio.wait_for(t2, timeout=1.0) == (True, "ok")
