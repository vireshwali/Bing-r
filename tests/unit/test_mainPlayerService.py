"""Unit tests for mainPlayerService — state classes, render thread, renderer.

Two testing strategies keep these tests CI-safe (headless, no GPU, no libmpv):

- ``RenderState`` / ``ThreadSync`` / ``SynchronizedState`` and the error-message
  builders are pure logic exercised directly.
- The render thread runs on a *real* ``QThread`` + ``QWaitCondition`` (OS-level,
  no display needed) with ``QOpenGLContext`` / ``QOpenGLFramebufferObject``
  mocked at module level, so the full render loop, FBO reuse/recreation and
  stop coordination are verified without a GPU.
- The renderer lifecycle (init, surface, mpv init, FBO/render entry points,
  teardown) runs with a fake ``mpv`` module injected into ``sys.modules`` and a
  mocked GL/surface layer — so no ``libmpv`` binary is required on CI.
"""

import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSize

from bingr.services import mainPlayerService as mps

_MPV_ERROR_CODE_NAMES = ("LOADING_FAILED", "NOTHING_TO_PLAY", "UNKNOWN_FORMAT", "VO_INIT_FAILED", "AO_INIT_FAILED")
_MPV_EVENT_ID_NAMES = ("END_FILE", "LOG_MESSAGE", "FILE_LOADED", "START_FILE")

# Fallbacks match the python-mpv binding's values (used only when the real
# binding is unavailable, e.g. a CI runner without libmpv).
_FALLBACK_ERROR_CODES = {
    "LOADING_FAILED": -13,
    "NOTHING_TO_PLAY": -16,
    "UNKNOWN_FORMAT": -17,
    "VO_INIT_FAILED": -15,
    "AO_INIT_FAILED": -14,
}
_FALLBACK_EVENT_IDS = {"END_FILE": 7, "LOG_MESSAGE": 2, "FILE_LOADED": 8, "START_FILE": 6}
_FALLBACK_END_FILE_ERROR = 4


@pytest.fixture
def fakeMpv(mocker):
    """Inject a fake ``mpv`` module so production code never touches libmpv.

    Reads the real enum values when the binding is importable; falls back to
    matching constants otherwise. The fake is placed in ``sys.modules`` so the
    ``import mpv`` statements inside the renderer resolve to it.
    """
    try:
        import mpv as _real_mpv

        errorCodes = {n: int(getattr(_real_mpv.ErrorCode, n)) for n in _MPV_ERROR_CODE_NAMES}
        eventIds = {n: int(getattr(_real_mpv.MpvEventID, n)) for n in _MPV_EVENT_ID_NAMES}
        endFileError = int(_real_mpv.MpvEventEndFile.ERROR)
    except (ImportError, OSError, AttributeError):
        errorCodes = dict(_FALLBACK_ERROR_CODES)
        eventIds = dict(_FALLBACK_EVENT_IDS)
        endFileError = _FALLBACK_END_FILE_ERROR

    fake = SimpleNamespace(
        MpvGlGetProcAddressFn=lambda fn: ("resolver", fn),
        MPV=MagicMock(),
        MpvRenderContext=MagicMock(),
        ErrorCode=SimpleNamespace(**errorCodes),
        MpvEventID=SimpleNamespace(**eventIds),
        MpvEventEndFile=SimpleNamespace(ERROR=endFileError),
    )
    mocker.patch.dict(sys.modules, {"mpv": fake})
    return fake


def _waitUntil(predicate, timeout=5.0):
    """Poll ``predicate()`` with short sleeps; return True when it succeeds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class TestRenderState:
    def testInitialState(self):
        state = mps.RenderState()
        assert state.renderFBO is None
        assert state.displayFBO is None
        assert state.videoSize == QSize()
        assert state.shouldRender is False
        assert state.renderingActive is True

    def testRequestAndClearRender(self):
        state = mps.RenderState()
        state.requestRender()
        assert state.shouldRender is True
        state.clearRenderRequest()
        assert state.shouldRender is False

    def testUpdateVideoSizeSameSizeNoOp(self):
        state = mps.RenderState()
        assert state.updateVideoSize(QSize(1920, 1080)) is True
        state.clearRenderRequest()

        assert state.updateVideoSize(QSize(1920, 1080)) is False
        assert state.videoSize == QSize(1920, 1080)
        assert state.shouldRender is False  # unchanged size must not request a render

    def testUpdateVideoSizeChangedRequestsRender(self):
        state = mps.RenderState()
        assert state.updateVideoSize(QSize(1920, 1080)) is True
        assert state.videoSize == QSize(1920, 1080)
        assert state.shouldRender is True

    def testSetAndSwapFBOs(self):
        state = mps.RenderState()
        renderFbo = MagicMock()
        displayFbo = MagicMock()

        state.setFBOs(renderFbo, displayFbo)
        assert state.renderFBO is renderFbo
        assert state.displayFBO is displayFbo

        state.swapFBOs()
        assert state.renderFBO is displayFbo
        assert state.displayFBO is renderFbo

    def testClearFBOs(self):
        state = mps.RenderState()
        state.setFBOs(MagicMock(), MagicMock())
        state.clearFBOs()
        assert state.renderFBO is None
        assert state.displayFBO is None

    def testStopRendering(self):
        state = mps.RenderState()
        state.stopRendering()
        assert state.renderingActive is False

    def testNeedsFboRecreationWhenMissing(self):
        state = mps.RenderState()
        assert state.needsFboRecreation(QSize(1280, 720)) is True

    def testNeedsFboRecreationOnSizeChange(self):
        state = mps.RenderState()
        state.setFBOs(MagicMock(size=lambda: QSize(1280, 720)), MagicMock(size=lambda: QSize(1280, 720)))
        assert state.needsFboRecreation(QSize(640, 480)) is True

    def testNeedsFboRecreationFalseWhenMatching(self):
        state = mps.RenderState()
        state.setFBOs(MagicMock(size=lambda: QSize(640, 480)), MagicMock(size=lambda: QSize(640, 480)))
        assert state.needsFboRecreation(QSize(640, 480)) is False


class TestThreadSync:
    def testLockUnlock(self):
        sync = mps.ThreadSync()
        sync.lock()
        sync.unlock()  # must not deadlock

    def testWaitWakesOnWakeOne(self):
        sync = mps.ThreadSync()
        woken = []

        def waiter():
            sync.lock()
            sync.wait()
            woken.append("woken")
            sync.unlock()

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)  # let the waiter block on the condition
        sync.wakeOne()
        t.join(timeout=2.0)

        assert not t.is_alive()
        assert woken == ["woken"]


class TestSynchronizedState:
    def testLockedYieldsStateAndSync(self):
        ss = mps.SynchronizedState()
        with ss.locked() as (state, sync):
            assert isinstance(state, mps.RenderState)
            assert isinstance(sync, mps.ThreadSync)

    def testLockReleasedAfterContext(self):
        ss = mps.SynchronizedState()
        with ss.locked():
            pass
        # A second acquisition must succeed; a stuck lock would deadlock here.
        with ss.locked():
            pass

    def testMutationsInsideLockVisibleOutside(self):
        ss = mps.SynchronizedState()
        with ss.locked() as (state, _sync):
            state.requestRender()
        assert ss._state.shouldRender is True


class TestGetProcAddress:
    def testNoContextReturnsZero(self, mocker):
        mocker.patch.object(mps.QOpenGLContext, "currentContext", return_value=None)
        assert mps.getProcAddress(None, b"glClear") == 0

    def testWithContextReturnsAddress(self, mocker):
        ctx = mocker.patch.object(mps.QOpenGLContext, "currentContext")
        ctx.return_value.getProcAddress.return_value = 12345
        assert mps.getProcAddress(None, b"glClear") == 12345


class TestRenderThread:
    @pytest.fixture
    def thread(self):
        return mps.MpvOffscreenRenderThread()

    def testAcquireYieldsStateAndSync(self, thread):
        with thread.acquire() as (state, sync):
            assert isinstance(state, mps.RenderState)
            assert isinstance(sync, mps.ThreadSync)

    def testPrepareStoresContexts(self, thread):
        ctx, shared, surface = MagicMock(), MagicMock(), MagicMock()

        thread.prepare(ctx, shared, surface)

        assert thread._ctx is ctx
        assert thread._sharedContext is shared
        assert thread._surface is surface

    def testRequestRenderRequestsAndWakes(self, thread):
        thread.requestRender()
        with thread.acquire() as (state, _sync):
            assert state.shouldRender is True

    def testUpdateSizeSetsVideoSizeAndWakes(self, thread):
        thread.updateSize(QSize(640, 480))
        with thread.acquire() as (state, _sync):
            assert state.videoSize == QSize(640, 480)
            assert state.shouldRender is True

    def testStopOnNeverStartedThread(self, thread):
        thread.stop()  # wait() on a non-started QThread returns immediately
        with thread.acquire() as (state, _sync):
            assert state.renderingActive is False

    def testCleanupReleasesState(self, thread):
        thread.cleanup()
        with thread.acquire() as (state, _sync):
            assert state.renderFBO is None
            assert state.displayFBO is None
        assert thread._glContext is None
        assert thread._ctx is None
        assert thread._surface is None

    def testCleanupReleasesGlContext(self, mocker):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        thread = mps.MpvOffscreenRenderThread()
        ctx = MagicMock()
        thread._glContext = ctx
        glCtx.currentContext.return_value = ctx

        thread.cleanup()

        ctx.doneCurrent.assert_called_once()
        assert thread._glContext is None

    def testCleanupSkipsDoneCurrentForForeignContext(self, mocker):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        thread = mps.MpvOffscreenRenderThread()
        ctx = MagicMock()
        thread._glContext = ctx
        glCtx.currentContext.return_value = MagicMock()  # different context

        thread.cleanup()

        ctx.doneCurrent.assert_not_called()
        assert thread._glContext is None

    def testCleanupToleratesDoneCurrentError(self, mocker):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        thread = mps.MpvOffscreenRenderThread()
        ctx = MagicMock()
        ctx.doneCurrent.side_effect = RuntimeError("context lost")
        thread._glContext = ctx
        glCtx.currentContext.return_value = ctx

        thread.cleanup()

        assert thread._glContext is None

    def _mockGl(self, mocker, fboSize=None):
        fboSize = fboSize if fboSize is not None else QSize(640, 480)
        fbos = []

        def fboFactory(*_args, **_kwargs):
            fbo = MagicMock()
            fbo.size.return_value = fboSize
            fbo.handle.return_value = 7
            fbos.append(fbo)
            return fbo

        mocker.patch.object(mps, "QOpenGLFramebufferObject", side_effect=fboFactory)
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        glCtx.return_value.create.return_value = True
        glCtx.return_value.makeCurrent.return_value = True
        glCtx.currentContext.return_value.functions.return_value = MagicMock()
        return fbos

    @staticmethod
    def _runLoopOnMainThread(thread, driverFn):
        """Run ``_renderLoop()`` on the calling thread so coverage credits it.

        coverage.py cannot trace code executed inside a QThread (a native
        thread spawned by Qt), so the render loop is driven from the main
        thread while ``driverFn`` (a Python thread) pokes the state machine.
        The real QWaitCondition/QMutex coordination is still exercised.
        """
        driver = threading.Thread(target=driverFn, daemon=True)
        driver.start()
        try:
            thread._renderLoop()  # blocks until the driver calls stop()
        finally:
            driver.join(timeout=5.0)

    def testRenderLoopRendersOnRequestMainThread(self, mocker):
        fbos = self._mockGl(mocker)
        ctx = MagicMock()
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(ctx, MagicMock(), MagicMock())

        def driver():
            time.sleep(0.05)
            thread.requestRender()
            time.sleep(0.05)
            thread.stop()

        self._runLoopOnMainThread(thread, driver)

        ctx.render.assert_called_once()
        assert len(fbos) == 2  # render + display FBO

    def testRenderLoopReusesThenRecreatesFbosMainThread(self, mocker):
        fbos = self._mockGl(mocker)
        ctx = MagicMock()
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(ctx, MagicMock(), MagicMock())

        def driver():
            time.sleep(0.05)
            thread.requestRender()
            time.sleep(0.05)
            thread.updateSize(QSize(640, 480))  # same size → reuse
            time.sleep(0.05)
            thread.updateSize(QSize(1280, 720))  # different size → recreate
            time.sleep(0.05)
            thread.stop()

        self._runLoopOnMainThread(thread, driver)

        assert ctx.render.call_count >= 3
        assert len(fbos) == 4  # one recreation after the initial pair

    def testRunExecutesRenderLoopMainThread(self, mocker):
        fbos = self._mockGl(mocker)
        ctx = MagicMock()
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(ctx, MagicMock(), MagicMock())

        def driver():
            time.sleep(0.05)
            thread.requestRender()
            time.sleep(0.05)
            thread.stop()

        driver = threading.Thread(target=driver, daemon=True)
        driver.start()
        try:
            thread.run()  # main thread → traced by coverage
        finally:
            driver.join(timeout=5.0)

        ctx.render.assert_called_once()
        assert len(fbos) == 2

    def testStopWakesIdleThread(self, mocker):
        self._mockGl(mocker)
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(MagicMock(), MagicMock(), MagicMock())
        thread.start()

        thread.stop()  # must not hang: wakes the idle wait and joins

        assert thread.isFinished()

    def testRunSkipsWhenNotPrepared(self):
        thread = mps.MpvOffscreenRenderThread()

        thread.run()  # no surface/sharedContext → early return, no GL touched

        assert thread._glContext is None

    def testRunSkipsWhenContextCreateFails(self, mocker):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        glCtx.return_value.create.return_value = False
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(MagicMock(), MagicMock(), MagicMock())

        thread.run()

        glCtx.return_value.makeCurrent.assert_not_called()

    def testRunSkipsWhenMakeCurrentFails(self, mocker):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        glCtx.return_value.create.return_value = True
        glCtx.return_value.makeCurrent.return_value = False
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(MagicMock(), MagicMock(), MagicMock())

        thread.run()

        glCtx.return_value.doneCurrent.assert_not_called()

    def testRenderLoopBreaksWhenStoppedBeforeRender(self, mocker):
        self._mockGl(mocker)
        thread = mps.MpvOffscreenRenderThread()
        thread.prepare(MagicMock(), MagicMock(), MagicMock())
        thread.requestRender()  # shouldRender True
        thread.stop()  # renderingActive False; wait() no-ops on a non-started thread

        thread._renderLoop()  # acquires → skips wait → breaks on !renderingActive

    def testRenderLoopSkipsWhenNoContext(self, mocker):
        self._mockGl(mocker)
        thread = mps.MpvOffscreenRenderThread()  # _ctx is None (never prepared)
        thread.requestRender()

        def driver():
            time.sleep(0.05)
            thread.stop()

        self._runLoopOnMainThread(thread, driver)  # `continue` path, no crash


class TestErrorMessageBuilders:
    """Pure string logic on the renderer — no Qt/GL/mpv instance needed."""

    @staticmethod
    def _renderer(logBuffer=None):
        renderer = mps.MpvOffscreenRenderer.__new__(mps.MpvOffscreenRenderer)
        renderer._logBuffer = list(logBuffer) if logBuffer else []
        return renderer

    def testMpvErrorTitleMapping(self, fakeMpv):
        ec = fakeMpv.ErrorCode
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(ec.LOADING_FAILED) == "Stream Unavailable"
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(ec.NOTHING_TO_PLAY) == "No Playable Streams"
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(ec.UNKNOWN_FORMAT) == "Unsupported Format"
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(ec.VO_INIT_FAILED) == "Video Output Error"
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(ec.AO_INIT_FAILED) == "Audio Output Error"
        assert mps.MpvOffscreenRenderer._mpvErrorTitle(99999) == "Playback Error"

    def testBuildErrorMessageEmptyLogUsesDefaults(self, fakeMpv):
        ec = fakeMpv.ErrorCode
        renderer = self._renderer()

        title, detail = renderer._buildErrorMessage(ec.LOADING_FAILED)
        assert title == "Stream Unavailable"
        assert "could not be loaded" in detail

        title, detail = renderer._buildErrorMessage(ec.NOTHING_TO_PLAY)
        assert title == "No Playable Streams"
        assert "No audio or video streams" in detail

        title, detail = renderer._buildErrorMessage(ec.UNKNOWN_FORMAT)
        assert title == "Unsupported Format"
        assert "could not be recognized" in detail

        title, detail = renderer._buildErrorMessage(ec.VO_INIT_FAILED)
        assert title == "Video Output Error"
        assert "video output" in detail

        title, detail = renderer._buildErrorMessage(ec.AO_INIT_FAILED)
        assert title == "Audio Output Error"
        assert "audio output" in detail

        title, detail = renderer._buildErrorMessage(12345)
        assert title == "Playback Error"
        assert "error occurred during playback" in detail

    def testBuildErrorMessageUsesLogDetail(self, fakeMpv):
        renderer = self._renderer(["[http] Failed to open https://x: Server returned 404 Not Found"])
        title, detail = renderer._buildErrorMessage(fakeMpv.ErrorCode.LOADING_FAILED)
        assert title == "Stream Unavailable"
        assert "HTTP 404" in detail

    @pytest.mark.parametrize(
        "code,reason",
        [
            ("401", "Authorization required"),
            ("403", "Access denied"),
            ("404", "Not found"),
            ("408", "Request timed out"),
            ("410", "Gone"),
            ("429", "Too many requests"),
            ("500", "Internal server error"),
            ("502", "Bad gateway"),
            ("503", "Service unavailable"),
            ("504", "Gateway timeout"),
        ],
    )
    def testHumanHttpErrorKnownCodes(self, code, reason):
        msg = mps.MpvOffscreenRenderer._humanHttpError(f"[http] Failed: Server returned {code}")
        assert f"HTTP {code} ({reason})" in msg

    def testHumanHttpErrorUnknownCode(self):
        msg = mps.MpvOffscreenRenderer._humanHttpError("[http] Failed: Server returned 451")
        assert "HTTP 451" in msg
        assert "could not be loaded" in msg

    def testHumanHttpErrorNoStatusCode(self):
        assert mps.MpvOffscreenRenderer._humanHttpError("[http] Failed to open") == ""

    def testHumanNetworkErrorTimedOut(self):
        msg = mps.MpvOffscreenRenderer._humanNetworkError("[network] Connection timed out")
        assert "timed out" in msg

    def testHumanNetworkErrorRefused(self):
        msg = mps.MpvOffscreenRenderer._humanNetworkError("[network] Connection refused")
        assert "refused" in msg

    def testHumanNetworkErrorResolve(self):
        msg = mps.MpvOffscreenRenderer._humanNetworkError("[network] Could not resolve host: x")
        assert "resolve the stream server address" in msg

    def testHumanNetworkErrorReset(self):
        msg = mps.MpvOffscreenRenderer._humanNetworkError("[network] Connection reset by peer")
        assert "reset" in msg

    def testHumanNetworkErrorGeneric(self):
        msg = mps.MpvOffscreenRenderer._humanNetworkError("[network] Something weird")
        assert "network problem" in msg

    def testHumanStreamErrorOpenFailure(self):
        msg = mps.MpvOffscreenRenderer._humanStreamError("[lavf] Failed to open this channel")
        assert "Could not open this channel" in msg

    def testHumanStreamErrorNoData(self):
        msg = mps.MpvOffscreenRenderer._humanStreamError("[hls] no data available")
        assert "no playable data" in msg

    def testHumanStreamErrorUnsupported(self):
        msg = mps.MpvOffscreenRenderer._humanStreamError("[ffmpeg] Unsupported format")
        assert "not supported" in msg

    def testHumanStreamErrorGeneric(self):
        msg = mps.MpvOffscreenRenderer._humanStreamError("[ffmpeg] Some weird failure")
        assert "unexpected error" in msg

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("failed to open the file", True),
            ("could not open the file", True),
            ("file not open", True),
            ("all good here", False),
        ],
    )
    def testLooksLikeOpenFailure(self, line, expected):
        assert mps.MpvOffscreenRenderer._looksLikeOpenFailure(line) is expected

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("connection refused", True),
            ("could not resolve host", True),
            ("timed out waiting", True),
            ("connection reset", True),
            ("all good here", False),
        ],
    )
    def testLooksLikeNetworkError(self, line, expected):
        assert mps.MpvOffscreenRenderer._looksLikeNetworkError(line) is expected

    def testMatchHttpErrorPicksHttpErrorLine(self):
        renderer = self._renderer(["[tcp] connection ok", "[http] Failed: Server returned 500 Internal server error"])
        line = renderer._matchHttpError()
        assert line is not None
        assert "HTTP 500" in mps.MpvOffscreenRenderer._humanHttpError(line)

    def testMatchOpenFailure(self):
        renderer = self._renderer(["[lavf] Could not open 'https://x'"])
        line = renderer._matchOpenFailure()
        assert line is not None
        assert "Could not open" in line

    def testMatchNetworkError(self):
        renderer = self._renderer(["[tcp] Connection refused"])
        line = renderer._matchNetworkError()
        assert line is not None
        assert "refused" in line

    def testMatchStreamLogError(self):
        renderer = self._renderer(["[ffmpeg] stream error: failed"])
        line = renderer._matchStreamLogError()
        assert line is not None
        assert "stream error" in line

    def testExtractErrorDetailEmptyBuffer(self):
        assert self._renderer()._extractErrorDetail() == ""

    def testExtractErrorDetailPrefersHttpOverNetwork(self):
        renderer = self._renderer([
            "[tcp] Connection refused",
            "[http] Failed to open https://x: Server returned 404 Not Found",
        ])
        detail = renderer._extractErrorDetail()
        assert "HTTP 404" in detail

    def testExtractErrorDetailFallsBackToLastLine(self):
        renderer = self._renderer(["[hls] demuxer error: no data available"])
        detail = renderer._extractErrorDetail()
        assert "no playable data" in detail

    def testHumanizeRoutesToStreamError(self):
        detail = self._renderer()._humanize("[hls] no data")
        assert "no playable data" in detail

    def testHumanizeRoutesToNetworkError(self):
        detail = self._renderer()._humanize("[tcp] Connection refused")
        assert "refused" in detail


class TestOnMpvUpdate:
    def testDisposedIgnored(self):
        renderer = TestRendererCallbacks._renderer(disposed=True)
        renderer._renderThread = MagicMock()
        renderer._onMpvUpdate()
        renderer._renderThread.requestRender.assert_not_called()

    def testRequestsRenderWhenThreadReady(self):
        renderer = TestRendererCallbacks._renderer()
        renderer._renderThread = MagicMock()
        renderer._renderThreadReady = True
        renderer._onMpvUpdate()
        renderer._renderThread.requestRender.assert_called_once()

    def testSkipsWhenThreadNotReady(self):
        renderer = TestRendererCallbacks._renderer()
        renderer._renderThread = MagicMock()
        renderer._renderThreadReady = False
        renderer._onMpvUpdate()
        renderer._renderThread.requestRender.assert_not_called()


class TestRendererCallbacks:
    """Property-callback handlers — no GL, no real mpv, constructed via __new__."""

    @staticmethod
    def _renderer(parent=None, disposed=False):
        renderer = mps.MpvOffscreenRenderer.__new__(mps.MpvOffscreenRenderer)
        renderer._disposed = disposed
        renderer._parent = parent if parent is not None else MagicMock()
        renderer._logBuffer = []
        renderer._mpv = MagicMock()
        return renderer

    def testEmitSignalEmits(self):
        renderer = self._renderer()
        sig = MagicMock()
        renderer._emitSignal(sig, 1.5)
        sig.emit.assert_called_once_with(1.5)

    def testEmitSignalSwallowsRuntimeError(self):
        renderer = self._renderer()
        sig = MagicMock()
        sig.emit.side_effect = RuntimeError("deleted")
        renderer._emitSignal(sig, 42)  # must not raise

    def testOnEofReachedSchedulesReconnect(self):
        renderer = self._renderer()
        renderer._onEofReached("eof-reached", True)
        renderer._parent._scheduleReconnect.assert_called_once()

    def testOnEofReachedDisposedIgnored(self):
        renderer = self._renderer(disposed=True)
        renderer._onEofReached("eof-reached", True)
        renderer._parent._scheduleReconnect.assert_not_called()

    def testOnCachedDurationEmitsFloat(self):
        renderer = self._renderer()
        renderer._onCachedDuration("demuxer-cache-duration", "12.5")
        renderer._parent.bufferedSecondsChanged.emit.assert_called_once_with(12.5)

    def testOnCachedDurationNoneFallsBackToZero(self):
        renderer = self._renderer()
        renderer._onCachedDuration("demuxer-cache-duration", None)
        renderer._parent.bufferedSecondsChanged.emit.assert_called_once_with(0.0)

    def testOnCachedDurationUnparseableFallsBackToZero(self):
        renderer = self._renderer()
        renderer._onCachedDuration("demuxer-cache-duration", "abc")
        renderer._parent.bufferedSecondsChanged.emit.assert_called_once_with(0.0)

    def testOnCachedDurationDisposedIgnored(self):
        renderer = self._renderer(disposed=True)
        renderer._onCachedDuration("demuxer-cache-duration", "5.0")
        renderer._parent.bufferedSecondsChanged.emit.assert_not_called()

    def testOnReadaheadEmitsFloat(self):
        renderer = self._renderer()
        renderer._onReadahead("demuxer-readahead-secs", 3)
        renderer._parent.readaheadSecsChanged.emit.assert_called_once_with(3.0)

    def testOnReadaheadBadValueFallsBackToZero(self):
        renderer = self._renderer()
        renderer._onReadahead("demuxer-readahead-secs", "nope")
        renderer._parent.readaheadSecsChanged.emit.assert_called_once_with(0.0)

    def testOnReadaheadDisposedIgnored(self):
        renderer = self._renderer(disposed=True)
        renderer._onReadahead("demuxer-readahead-secs", 3)
        renderer._parent.readaheadSecsChanged.emit.assert_not_called()

    def testOnDemuxerCacheStateNonDictIdle(self):
        renderer = self._renderer()
        renderer._onDemuxerCacheState("demuxer-cache-state", "junk")
        renderer._parent.bufferingStateChanged.emit.assert_called_once_with("idle")

    def testOnDemuxerCacheStateUnderrunBuffering(self):
        renderer = self._renderer()
        renderer._onDemuxerCacheState("demuxer-cache-state", {"underrun": True})
        renderer._parent.bufferingStateChanged.emit.assert_called_once_with("buffering")

    def testOnDemuxerCacheStatePlayingBumpsReadahead(self):
        renderer = self._renderer()
        renderer._mpv.demuxer_readahead_secs = 5
        renderer._onDemuxerCacheState("demuxer-cache-state", {"underrun": False})
        renderer._parent.bufferingStateChanged.emit.assert_called_once_with("playing")
        assert renderer._mpv.demuxer_readahead_secs == 40

    def testOnDemuxerCacheStatePlayingKeepsLargeReadahead(self):
        renderer = self._renderer()
        renderer._mpv.demuxer_readahead_secs = 50
        renderer._onDemuxerCacheState("demuxer-cache-state", {"underrun": False})
        assert renderer._mpv.demuxer_readahead_secs == 50

    def testOnDemuxerCacheStateUnderrunSkipsReadaheadBump(self):
        renderer = self._renderer()
        renderer._mpv.demuxer_readahead_secs = 5
        renderer._onDemuxerCacheState("demuxer-cache-state", {"underrun": True})
        assert renderer._mpv.demuxer_readahead_secs == 5

    def testOnDemuxerCacheStateDisposedIgnored(self):
        renderer = self._renderer(disposed=True)
        renderer._onDemuxerCacheState("demuxer-cache-state", {"underrun": True})
        renderer._parent.bufferingStateChanged.emit.assert_not_called()


class TestOnMpvEvent:
    @staticmethod
    def _event(eid, data=None):
        event = MagicMock()
        event.event_id.value = eid
        event.data = data
        return event

    def testEndFileErrorEmitsAndClearsLogBuffer(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        renderer._logBuffer = ["[http] Server returned 404 Not Found"]
        end_file = MagicMock()
        end_file.reason = fakeMpv.MpvEventEndFile.ERROR
        end_file.error = 1

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.END_FILE, end_file))

        renderer._parent.errorOccurred.emit.assert_called_once()
        assert renderer._logBuffer == []

    def testEndFileWithoutErrorNoEmit(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        renderer._logBuffer = ["[http] x"]
        end_file = MagicMock()
        end_file.reason = 0  # EOF, not an error

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.END_FILE, end_file))

        renderer._parent.errorOccurred.emit.assert_not_called()
        assert renderer._logBuffer == ["[http] x"]

    def testEndFileErrorEmitFailureSwallowed(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        renderer._logBuffer = ["[http] x"]
        renderer._parent.errorOccurred.emit.side_effect = RuntimeError("deleted")
        end_file = MagicMock()
        end_file.reason = fakeMpv.MpvEventEndFile.ERROR
        end_file.error = 1

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.END_FILE, end_file))  # must not raise

        assert renderer._logBuffer == []  # buffer still cleared

    def testLogMessageErrorAppended(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        ev = MagicMock()
        ev.level = "error"
        ev.prefix = "ffmpeg"
        ev.text = "Server returned 404 Not Found"

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.LOG_MESSAGE, ev))

        assert renderer._logBuffer == ["[ffmpeg] Server returned 404 Not Found"]

    def testLogMessageWarnAppended(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        ev = MagicMock()
        ev.level = "warn"
        ev.prefix = "cplayer"
        ev.text = "dropped frames"

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.LOG_MESSAGE, ev))

        assert renderer._logBuffer == ["[cplayer] dropped frames"]

    def testLogMessageInfoIgnored(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        ev = MagicMock()
        ev.level = "info"
        ev.prefix = "cplayer"
        ev.text = "started playback"

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.LOG_MESSAGE, ev))

        assert renderer._logBuffer == []

    def testLogMessageBufferCappedAtTwenty(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer()
        renderer._logBuffer = [f"[x] {i}" for i in range(20)]
        ev = MagicMock()
        ev.level = "error"
        ev.prefix = "p"
        ev.text = "overflow"

        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.LOG_MESSAGE, ev))

        assert len(renderer._logBuffer) == 20

    def testDisposedIgnoresEvents(self, fakeMpv):
        renderer = TestRendererCallbacks._renderer(disposed=True)
        renderer._onMpvEvent(self._event(fakeMpv.MpvEventID.END_FILE, MagicMock()))
        renderer._parent.errorOccurred.emit.assert_not_called()


class TestRendererLifecycle:
    @pytest.fixture
    def glEnv(self, mocker, fakeMpv):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        glCtx.currentContext.return_value.format.return_value = ("fmt",)
        surf = mocker.patch.object(mps, "QOffscreenSurface")
        gui = mocker.patch.object(mps, "QGuiApplication", create=True)
        gui.primaryScreen.return_value.refreshRate.return_value = 60
        return {"glCtx": glCtx, "surf": surf, "gui": gui}

    @pytest.fixture
    def parent(self):
        p = MagicMock()
        p._pendingUrl = None
        return p

    def testInitSetsUpRenderer(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)

        assert renderer._parent is parent
        assert renderer._disposed is False
        assert renderer._surfaceReady is False
        assert renderer._renderThreadReady is False
        assert isinstance(renderer._renderThread, mps.MpvOffscreenRenderThread)
        parent.onSurfaceReady.connect.assert_called_once_with(renderer._onConfigureSurface)

    def testOnConfigureSurfacePreparesSurface(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)

        renderer._onConfigureSurface()

        assert renderer._surfaceReady is True
        parent.update.assert_called_once()

    def testInitializeMpvContextBuildsPlayerAndRenderContext(self, glEnv, parent, fakeMpv):
        renderer = mps.MpvOffscreenRenderer(parent)

        renderer._initializeMpvContext()

        fakeMpv.MPV.assert_called_once()
        assert renderer._mpv is fakeMpv.MPV.return_value
        assert renderer._ctx is fakeMpv.MpvRenderContext.return_value
        assert renderer._renderThreadReady is True
        assert renderer._renderThread._ctx is renderer._ctx
        assert parent._mpv is renderer._mpv
        fakeMpv.MPV.return_value.observe_property.assert_any_call("eof-reached", renderer._onEofReached)
        fakeMpv.MPV.return_value.register_event_callback.assert_called_once_with(renderer._onMpvEvent)

    def testInitializeMpvContextTerminatesExistingPlayer(self, glEnv, parent, fakeMpv):
        renderer = mps.MpvOffscreenRenderer(parent)
        old = MagicMock()
        renderer._mpv = old

        renderer._initializeMpvContext()

        old.terminate.assert_called_once()
        assert renderer._mpv is fakeMpv.MPV.return_value

    def testInitializeMpvContextToleratesTerminateError(self, glEnv, parent, fakeMpv):
        renderer = mps.MpvOffscreenRenderer(parent)
        old = MagicMock()
        old.terminate.side_effect = RuntimeError("dead")
        renderer._mpv = old

        renderer._initializeMpvContext()  # must not raise

        assert renderer._mpv is fakeMpv.MPV.return_value

    def testInitializeMpvContextPlaysPendingUrl(self, glEnv, parent, fakeMpv):
        parent._pendingUrl = "https://x/live.m3u8"
        renderer = mps.MpvOffscreenRenderer(parent)

        renderer._initializeMpvContext()

        fakeMpv.MPV.return_value.play.assert_called_once_with("https://x/live.m3u8")
        assert parent._pendingUrl is None

    def testCreateFramebufferObjectInitializesAndUpdatesSize(self, glEnv, parent, mocker):
        base = mocker.patch.object(
            mps.QQuickFramebufferObject.Renderer,
            "createFramebufferObject",
            return_value="fbo",
        )
        renderer = mps.MpvOffscreenRenderer(parent)

        result = renderer.createFramebufferObject(QSize(640, 480))

        assert result == "fbo"
        assert renderer._videoSize == QSize(640, 480)
        base.assert_called_once_with(renderer, QSize(640, 480))

    def testCreateFramebufferObjectDisposedDelegatesToBase(self, glEnv, parent, mocker):
        base = mocker.patch.object(
            mps.QQuickFramebufferObject.Renderer,
            "createFramebufferObject",
            return_value="fbo",
        )
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._disposed = True

        assert renderer.createFramebufferObject(QSize(100, 100)) == "fbo"
        base.assert_called_once_with(renderer, QSize(100, 100))

    def testRenderDisposedReturns(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._disposed = True
        renderer.render()  # must not raise

    def testRenderEmitsSurfaceReadyWhenNotReady(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)

        renderer.render()

        parent.onSurfaceReady.emit.assert_called_once()

    def testRenderReturnsWhenThreadNotReady(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._surfaceReady = True

        renderer.render()  # _renderThreadReady False → returns without starting

        assert renderer._rendererThreadStarted is False

    def testRenderStartsThreadOnce(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._surfaceReady = True
        renderer._renderThreadReady = True
        start = MagicMock()
        renderer._renderThread.start = start

        renderer.render()
        renderer.render()

        start.assert_called_once()
        assert renderer._rendererThreadStarted is True

    def testRenderBlitsDisplayFbo(self, glEnv, parent, mocker):
        blit = mocker.patch.object(mps.QOpenGLFramebufferObject, "blitFramebuffer")
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._surfaceReady = True
        renderer._renderThreadReady = True
        renderer._rendererThreadStarted = True
        display = MagicMock()
        display.isValid.return_value = True
        renderer.framebufferObject = MagicMock(return_value="target")
        with renderer._renderThread.acquire() as (state, _sync):
            state.setFBOs(MagicMock(), display)

        renderer.render()

        blit.assert_called_once_with("target", display)


class TestCleanupTeardown:
    @pytest.fixture
    def glEnv(self, mocker, fakeMpv):
        glCtx = mocker.patch.object(mps, "QOpenGLContext")
        glCtx.currentContext.return_value.format.return_value = ("fmt",)
        surf = mocker.patch.object(mps, "QOffscreenSurface")
        gui = mocker.patch.object(mps, "QGuiApplication", create=True)
        gui.primaryScreen.return_value.refreshRate.return_value = 60
        return {"glCtx": glCtx, "surf": surf, "gui": gui}

    @pytest.fixture
    def parent(self):
        p = MagicMock()
        p._pendingUrl = None
        return p

    def _renderer(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)
        renderer._renderThread = MagicMock()
        renderer._ctx = MagicMock()
        renderer._mpv = MagicMock()
        renderer._surface = MagicMock()
        return renderer

    def testCleanupTearsDownInOrder(self, glEnv, parent):
        renderer = self._renderer(glEnv, parent)
        thread, ctx, mpvPlayer, surface = (
            renderer._renderThread,
            renderer._ctx,
            renderer._mpv,
            renderer._surface,
        )
        calls = []
        thread.stop.side_effect = lambda: calls.append("stop")
        thread.cleanup.side_effect = lambda: calls.append("thread_cleanup")
        ctx.free.side_effect = lambda: calls.append("free")
        mpvPlayer.unregister_event_callback.side_effect = lambda *a: calls.append("unregister")
        mpvPlayer.stop.side_effect = lambda: calls.append("mpv_stop")
        mpvPlayer.terminate.side_effect = lambda: calls.append("mpv_terminate")
        surface.destroy.side_effect = lambda: calls.append("destroy")
        parent.onSurfaceReady.disconnect.side_effect = lambda *a: calls.append("disconnect")

        renderer.cleanup()

        assert renderer._disposed is True
        assert renderer._parent is None
        assert renderer._renderThread is None
        assert renderer._ctx is None
        assert renderer._mpv is None
        assert renderer._surface is None
        assert calls == ["stop", "thread_cleanup", "free", "unregister", "mpv_stop", "mpv_terminate", "disconnect", "destroy"]
        assert mpvPlayer.unobserve_property.call_count == 4

    def testCleanupToleratesErrorsEverywhere(self, glEnv, parent):
        renderer = self._renderer(glEnv, parent)
        renderer._renderThread.stop.side_effect = RuntimeError
        renderer._renderThread.cleanup.side_effect = RuntimeError
        renderer._ctx.free.side_effect = RuntimeError
        renderer._mpv.unregister_event_callback.side_effect = RuntimeError
        renderer._mpv.unobserve_property.side_effect = RuntimeError
        renderer._mpv.stop.side_effect = RuntimeError
        renderer._mpv.terminate.side_effect = RuntimeError
        renderer._surface.destroy.side_effect = RuntimeError
        parent.onSurfaceReady.disconnect.side_effect = RuntimeError

        renderer.cleanup()  # must not raise; all state released

        assert renderer._renderThread is None
        assert renderer._ctx is None
        assert renderer._mpv is None
        assert renderer._surface is None

    def testCleanupPartialState(self, glEnv, parent):
        renderer = mps.MpvOffscreenRenderer(parent)  # _mpv/_ctx not yet initialized

        renderer.cleanup()

        assert renderer._disposed is True
        assert renderer._parent is None
        assert renderer._mpv is None


class TestTeardownGuards:
    """Early-return / exception branches of the individual teardown steps."""

    class RaisingParent:
        def __init__(self):
            self.onSurfaceReady = MagicMock()

        def __setattr__(self, name, value):
            if name == "_mpv":
                raise RuntimeError("readonly")
            super().__setattr__(name, value)

    def _renderer(self, parent=None):
        renderer = TestRendererCallbacks._renderer(parent)
        renderer._renderThread = MagicMock()
        renderer._ctx = MagicMock()
        renderer._mpv = MagicMock()
        renderer._surface = MagicMock()
        return renderer

    def testDetachFromParentSkipsWhenNoParent(self):
        renderer = self._renderer()
        renderer._parent = None

        renderer._detachFromParent()  # early return

    def testDetachFromParentToleratesMpvSetError(self):
        renderer = self._renderer(parent=self.RaisingParent())

        renderer._detachFromParent()  # parent._mpv = None raises → swallowed

    def testDetachFromParentToleratesDisconnectError(self):
        parent = MagicMock()
        parent.onSurfaceReady.disconnect.side_effect = RuntimeError("gone")
        renderer = self._renderer(parent=parent)

        renderer._detachFromParent()  # must not raise

    def testTeardownRenderThreadSkipsWhenMissing(self):
        renderer = self._renderer()
        renderer._renderThread = None

        renderer._teardownRenderThread()  # early return

    def testTeardownRenderContextSkipsWhenMissing(self):
        renderer = self._renderer()
        renderer._ctx = None

        renderer._teardownRenderContext()  # early return

    def testTeardownSurfaceSkipsWhenMissing(self):
        renderer = self._renderer()
        renderer._surface = None

        renderer._teardownSurface()  # early return
