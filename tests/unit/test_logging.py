import logging

import pytest

from tests.conftest import RUNTIME_DIR


@pytest.fixture(autouse=True)
def _resetLogging():
    bingrLogger = logging.getLogger("bingr")
    bingrLogger.setLevel(logging.NOTSET)
    bingrLogger.handlers.clear()
    for name in ("alembic.runtime.migration", "alembic.runtime.plugins"):
        logging.getLogger(name).setLevel(logging.NOTSET)


class TestSetupLogging:
    @pytest.fixture
    def mockConfig(self, monkeypatch, request):
        class FakeConfig:
            def get(self, key: str, default: str = "") -> str:
                if key == "log.level":
                    return getattr(self, "_log_level", "INFO")
                return default

            def logDir(self):
                return RUNTIME_DIR / "logs" / request.node.name

        fake = FakeConfig()

        def fakeGetConfig():
            return fake

        monkeypatch.setattr("bingr.common.logging.getConfig", fakeGetConfig)
        return fake

    def testDefaultLevelIsInfo(self, mockConfig, caplog):
        from bingr.common.logging import setupLogging

        setupLogging()
        assert logging.getLogger("bingr").level == logging.INFO

    def testDebugLevel(self, mockConfig, caplog):
        from bingr.common.logging import setupLogging

        mockConfig._log_level = "DEBUG"
        setupLogging()
        assert logging.getLogger("bingr").level == logging.DEBUG

    @pytest.mark.parametrize(
        "levelName",
        [
            pytest.param("WARNING", id="warning"),
            pytest.param("ERROR", id="error"),
        ],
    )
    def testCustomLevels(self, mockConfig, levelName):
        from bingr.common.logging import setupLogging

        mockConfig._log_level = levelName
        setupLogging()
        expected = getattr(logging, levelName)
        assert logging.getLogger("bingr").level == expected

    def testInvalidLevelDefaultsToInfo(self, mockConfig):
        from bingr.common.logging import setupLogging

        mockConfig._log_level = "NONEXISTENT"
        setupLogging()
        assert logging.getLogger("bingr").level == logging.INFO

    def testAlembicPluginLevelSetToWarning(self, mockConfig):
        from bingr.common.logging import setupLogging

        setupLogging()
        assert logging.getLogger("alembic.runtime.plugins").level == logging.WARNING
