"""Real ffprobe integration tests for FfprobeService — no mocks.

Runs the actual ``ffprobe`` binary (via QProcess subprocess) against well-known
public HLS endpoints, mirroring the HttpProbeService integration suite. The Qt
event loop is pumped manually (``processEvents``) from the asyncio test loop,
matching how QtAsyncio drives it in the app.

A locally-generated media file is also probed so the full subprocess → signal →
future path is exercised deterministically without network.
"""

import asyncio
import shutil
import subprocess

import pytest
from PySide6.QtCore import QCoreApplication

from bingr.services.ffprobeService import FfprobeService

pytestmark = pytest.mark.external_http

GOOD_URLS = {
    "unified-tos": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
    "mux-x36xhzz": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    "mux-pts-shift": "https://test-streams.mux.dev/pts_shift/master.m3u8",
}

BAD_URLS = {
    "mux-missing": "https://test-streams.mux.dev/no-such-file-bingr-test.m3u8",
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
    return FfprobeService(timeoutSeconds=30.0, concurrency=4)


@pytest.fixture(scope="session")
def localMedia(_testsRuntime):
    """A tiny real media file generated once with ffmpeg (skipped if absent)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("ffmpeg not available to generate a local media fixture")
    out = _testsRuntime / "ffprobe_test_clip.mp4"
    if not out.exists():
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=1:size=64x64:rate=10",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(out),
            ],
            check=True,
        )
    return out


async def pumpUntil(predicate, timeoutSeconds=60.0):
    """Pump the Qt event loop until predicate() is true or timeout."""
    app = QCoreApplication.instance()
    assert app is not None, "QCoreApplication fixture must be active"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeoutSeconds
    while not predicate():
        if loop.time() >= deadline:
            pytest.fail("Timed out waiting for Qt process events")
        app.processEvents()
        await asyncio.sleep(0.01)


async def runValidate(service, url):
    task = asyncio.create_task(service.validate(url))
    await pumpUntil(task.done)
    return await task


async def runBatch(service, results, keyToUrl):
    task = asyncio.create_task(service.validateBatch(results, keyToUrl))
    await pumpUntil(task.done)
    await task


class TestFfprobeAgainstRealEndpoints:
    async def testGoodUrlValidates(self, service):
        ok, reason = await runValidate(service, GOOD_URLS["mux-x36xhzz"])
        assert ok is True
        assert reason == "ok"

    async def testMissingUrlFails(self, service):
        ok, reason = await runValidate(service, BAD_URLS["mux-missing"])
        assert ok is False
        assert reason  # a human-readable failure reason

    async def testDnsInvalidFails(self, service):
        ok, reason = await runValidate(service, BAD_URLS["dns-invalid"])
        assert ok is False
        assert reason

    async def testBatchDowngradesUnplayableUrls(self, service):
        results = {"good": True, "missing": True, "dns": True}
        keyToUrl = {
            "good": GOOD_URLS["unified-tos"],
            "missing": BAD_URLS["mux-missing"],
            "dns": BAD_URLS["dns-invalid"],
        }

        await runBatch(service, results, keyToUrl)

        assert results == {"good": True, "missing": False, "dns": False}

    async def testBatchSkipsAlreadyUnreachable(self, service):
        results = {"good": True, "dns": False}
        keyToUrl = {"good": GOOD_URLS["mux-pts-shift"], "dns": BAD_URLS["dns-invalid"]}

        await runBatch(service, results, keyToUrl)

        assert results == {"good": True, "dns": False}

    async def testOnResultCallbackReportsEachUrl(self, service):
        calls = []
        url = GOOD_URLS["mux-x36xhzz"]
        task = asyncio.create_task(
            service.validate(url, onResult=lambda u, ok, reason: calls.append((u, ok, reason)))
        )
        await pumpUntil(task.done)
        await task
        assert calls == [(url, True, "ok")]


class TestFfprobeAgainstLocalFile:
    async def testLocalMediaFileValidates(self, service, localMedia):
        ok, reason = await runValidate(service, str(localMedia))
        assert ok is True
        assert reason == "ok"

    async def testMissingLocalFileFails(self, service, _testsRuntime):
        ok, reason = await runValidate(service, str(_testsRuntime / "no-such-file.mp4"))
        assert ok is False
        assert reason
