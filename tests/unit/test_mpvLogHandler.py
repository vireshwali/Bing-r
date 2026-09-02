"""Unit tests for mpv log handling — _mpvLogHandler and level mapping."""

import logging

from bingr.services.mainPlayerService import (
    _MPV_LEVEL_MAP,
    _SETTINGS_LEVEL_MAP,
    _mpvLogHandler,
)


class TestMpvLevelMap:
    def testFatalMapsToCritical(self):
        assert _MPV_LEVEL_MAP["fatal"] == logging.CRITICAL

    def testErrorMapsToError(self):
        assert _MPV_LEVEL_MAP["error"] == logging.ERROR

    def testWarnMapsToWarning(self):
        assert _MPV_LEVEL_MAP["warn"] == logging.WARNING

    def testInfoMapsToInfo(self):
        assert _MPV_LEVEL_MAP["info"] == logging.INFO

    def testVerboseLevelsMapToDebug(self):
        for level in ("v", "debug", "trace"):
            assert _MPV_LEVEL_MAP[level] == logging.DEBUG


class TestSettingsLevelMap:
    def testNoneNormalisedToNo(self):
        assert _SETTINGS_LEVEL_MAP["none"] == "no"


class TestMpvLogHandler:
    def testEmitsAtMappedLevel(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("warn", "ffmpeg", "hls: mime type is not rfc8216 compliant")
        record = next(r for r in caplog.records if "[ffmpeg]" in r.message)
        assert record.levelno == logging.WARNING
        assert "hls: mime type is not rfc8216 compliant" in record.message

    def testPrefixIncludedInMessage(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("info", "cplayer", "starting playback")
        assert any("[cplayer] starting playback" in r.message for r in caplog.records)

    def testUnknownLevelFallsBackToInfo(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("bogus-level", "ao", "weird")
        record = next(r for r in caplog.records if "weird" in r.message)
        assert record.levelno == logging.INFO

    def testBytesTextDecoded(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("error", "demux", b"binary-ish \xff message")
        assert any("binary-ish" in r.message for r in caplog.records)

    def testTrailingNewlineStripped(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("info", "vo", "frame dropped\n")
        record = next(r for r in caplog.records if "frame dropped" in r.message)
        assert not record.getMessage().endswith("\n")

    def testUsesDedicatedMpvLoggerName(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="bingr.mpv"):
            _mpvLogHandler("info", "cplayer", "hello")
        record = next(r for r in caplog.records if "hello" in r.message)
        assert record.name == "bingr.mpv"
