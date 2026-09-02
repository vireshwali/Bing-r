"""Unit tests for logStreamProxy — stdout/stderr routing into Python logging."""

import logging

import bingr.common.logStreamProxy as lspModule
from bingr.common.logStreamProxy import _LogStreamProxy, installStreamProxies


class FakeStream:
    def __init__(self):
        self.written = []
        self.flushed = False
        self.encoding = "utf-8"

    def write(self, text):
        self.written.append(text)
        return len(text)

    def flush(self):
        self.flushed = True


class TestLogStreamProxy:
    def testCompleteLineLoggedAtConfiguredLevel(self, caplog):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        with caplog.at_level(logging.INFO, logger="bingr.stdout"):
            proxy.write("mpv: some ffmpeg warning\n")
        assert any("mpv: some ffmpeg warning" in r.message for r in caplog.records)

    def testPassthroughWriteToOriginalStream(self):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        count = proxy.write("hello\n")
        assert count == 6
        assert original.written == ["hello\n"]

    def testEmptyAndWhitespaceLinesNotLogged(self, caplog):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        with caplog.at_level(logging.INFO, logger="bingr.stdout"):
            proxy.write("\n")
            proxy.write("   \n")
        assert caplog.records == []

    def testPartialLineBufferedUntilNewline(self, caplog):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        with caplog.at_level(logging.INFO, logger="bingr.stdout"):
            proxy.write("par")
            proxy.write("tial\n")
            proxy.write("more")
            proxy.flush()
        messages = [r.message for r in caplog.records]
        assert "partial" in messages
        assert "more" in messages

    def testMultiLineWriteEmitsEachLine(self, caplog):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.WARNING)
        with caplog.at_level(logging.WARNING, logger="bingr.stderr"):
            proxy.write("line one\nline two\n")
        messages = [r.message for r in caplog.records]
        assert "line one" in messages
        assert "line two" in messages

    def testFlushEmitsTrailingPartialLine(self, caplog):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        with caplog.at_level(logging.INFO, logger="bingr.stdout"):
            proxy.write("no trailing newline")
            proxy.flush()
        assert any("no trailing newline" in r.message for r in caplog.records)

    def testFlushDelegatesToOriginal(self):
        original = FakeStream()
        proxy = _LogStreamProxy(original, logging.getLogger("bingr.stdout"), logging.INFO)
        proxy.flush()
        assert original.flushed is True

    def testIsattyFalse(self):
        proxy = _LogStreamProxy(FakeStream(), logging.getLogger("bingr.stdout"), logging.INFO)
        assert proxy.isatty() is False


class TestInstallStreamProxies:
    def testInstallsProxiesOnSysStreams(self, monkeypatch):
        fakeOut, fakeErr = FakeStream(), FakeStream()
        monkeypatch.setattr(lspModule.sys, "stdout", fakeOut)
        monkeypatch.setattr(lspModule.sys, "stderr", fakeErr)
        # Reset module state so this test is independent of other tests.
        monkeypatch.setattr(lspModule, "_stdoutProxy", None)
        monkeypatch.setattr(lspModule, "_stderrProxy", None)

        installStreamProxies()

        try:
            assert isinstance(lspModule.sys.stdout, _LogStreamProxy)
            assert isinstance(lspModule.sys.stderr, _LogStreamProxy)
            assert lspModule.sys.stdout._original is fakeOut
            assert lspModule.sys.stderr._original is fakeErr
        finally:
            lspModule.sys.stdout = fakeOut
            lspModule.sys.stderr = fakeErr

    def testIdempotentNoDoubleWrapping(self, monkeypatch):
        fakeOut, fakeErr = FakeStream(), FakeStream()
        monkeypatch.setattr(lspModule.sys, "stdout", fakeOut)
        monkeypatch.setattr(lspModule.sys, "stderr", fakeErr)
        monkeypatch.setattr(lspModule, "_stdoutProxy", None)
        monkeypatch.setattr(lspModule, "_stderrProxy", None)

        installStreamProxies()
        firstOut = lspModule.sys.stdout
        installStreamProxies()

        try:
            assert lspModule.sys.stdout is firstOut
            assert not isinstance(firstOut._original, _LogStreamProxy)
        finally:
            lspModule.sys.stdout = fakeOut
            lspModule.sys.stderr = fakeErr

    def testStdoutAtInfoAndStderrAtWarning(self, monkeypatch, caplog):
        fakeOut, fakeErr = FakeStream(), FakeStream()
        monkeypatch.setattr(lspModule.sys, "stdout", fakeOut)
        monkeypatch.setattr(lspModule.sys, "stderr", fakeErr)
        monkeypatch.setattr(lspModule, "_stdoutProxy", None)
        monkeypatch.setattr(lspModule, "_stderrProxy", None)

        caplog.set_level(logging.DEBUG)
        installStreamProxies()
        try:
            lspModule.sys.stdout.write("info line\n")
            lspModule.sys.stderr.write("warn line\n")
        finally:
            lspModule.sys.stdout = fakeOut
            lspModule.sys.stderr = fakeErr

        levels = {r.message: r.levelno for r in caplog.records}
        assert levels.get("info line") == logging.INFO
        assert levels.get("warn line") == logging.WARNING
