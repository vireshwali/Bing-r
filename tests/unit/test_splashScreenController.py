"""Unit tests for splashScreenController."""

import bingr.controllers.splashScreenController as sscModule
from bingr.controllers.splashScreenController import SplashScreenController


class TestPublishProgressMsg:
    def testEmitsNonEmptyMessage(self):
        ctrl = SplashScreenController()
        received = []
        ctrl.progressMsg.connect(received.append)

        ctrl.publishProgressMsg("Loading database…")

        assert received == ["Loading database…"]

    def testEmptyStringNotEmitted(self):
        ctrl = SplashScreenController()
        received = []
        ctrl.progressMsg.connect(received.append)

        ctrl.publishProgressMsg("")

        assert received == []

    def testNoneNotEmitted(self):
        ctrl = SplashScreenController()
        received = []
        ctrl.progressMsg.connect(received.append)

        ctrl.publishProgressMsg(None)

        assert received == []

    def testWhitespaceIsTruthyAndEmitted(self):
        """Documents current behaviour: only falsy messages are suppressed."""
        ctrl = SplashScreenController()
        received = []
        ctrl.progressMsg.connect(received.append)

        ctrl.publishProgressMsg(" ")

        assert received == [" "]


class TestModuleRegistration:
    def testQmlImportMetadataSet(self):
        assert sscModule.QML_IMPORT_NAME == "bingr.controllers"
        assert sscModule.QML_IMPORT_MAJOR_VERSION == 1

    def testIsQObjectSubclass(self):
        from PySide6.QtCore import QObject

        assert issubclass(SplashScreenController, QObject)
