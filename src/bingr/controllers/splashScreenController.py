"""Splash screen controller — exposes init progress to QML."""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QmlElement

from bingr import __codename__, __version__
from bingr.common.config import getConfig
from bingr.services.systemHealthMonitorService import SystemHealthMonitorService

# To be used on the @QmlElement decorator
# (QML_IMPORT_MINOR_VERSION is optional)
QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
class SplashScreenController(QObject):
    """Qt property bag hooked into the QML splash screen.

    The ``progress`` property is writable from Python and automatically
    notifies QML bindings when it changes, so the splash can display
    live status messages such as "Loading database…".
    """

    # Argument is the name of the arg that we will use in QML connection
    progressMsg = Signal(str, arguments=["msg"])

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        logger.info("SplashScreenController initialized.")

    def publishProgressMsg(self, msg: str):
        if msg:
            self.progressMsg.emit(msg)

    @Property(str, constant=True)
    def appVersionSlug(self) -> str:
        return f"v{__version__} {__codename__}"

    def onAppBootComplete(self):
        # Close and clean up the splash window
        from bingr import runtime

        if not runtime.appEngineGlobal:
            logger.warning("appEngine is None, cannot continue further.")
            sys.exit(-1)

        for obj in QGuiApplication.topLevelWindows():
            if obj.objectName() == "splashWindow":
                obj.close()  # type: ignore
                obj.deleteLater()
                break

        # Load the main application
        runtime.appEngineGlobal.loadFromModule("ui", "App")

        # Start the system health monitor service
        cfg = getConfig()
        workspace = cfg.workspacePath()
        runtime.systemHealthMonitorService = SystemHealthMonitorService(workspace)
        runtime.systemHealthMonitorService.runAllChecksOnDemand()

    def initializeApp(self):
        from bingr.main import bootApp

        task = asyncio.create_task(bootApp(self, time.monotonic()))
        task.add_done_callback(lambda t: self.onAppBootComplete())
        self.boot_task = task

    @Slot()
    def doAppBoot(self):
        QTimer.singleShot(0, self.initializeApp)
