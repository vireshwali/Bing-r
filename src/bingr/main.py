"""Application entry point — boots the Qt Quick UI.

Sets QT_QUICK_CONTROLS_CONF, shows splash screen, initialises infra
asynchronously, then transitions to App.qml with a minimum 3s splash.
"""

# from PySide6.QtQml import QQmlDebuggingEnabler
# # 1. Authorize the debugging system explicitly
# QQmlDebuggingEnabler.enableDebugging(True)
# # 2. Hardcode the command-line argument directly into the Python argument list
# # This tricks the C++ engine into blocking at startup, bypassing shell isolation.
# if not any(arg.startswith("-qmljsdebugger") for arg in sys.argv):
#     sys.argv.append("-qmljsdebugger=port:10002,block")
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtCore import QTimer, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from bingr import qml_resources, runtime  # type: ignore # noqa: F401
from bingr.common.appNetworkFactory import AppNetworkAccessManagerFactory
from bingr.common.cache import initialize as initCache
from bingr.common.commonUtils import isNuitka, trimHeap
from bingr.common.config import getConfig
from bingr.common.logging import setupLogging
from bingr.controllers.addNewSourcesController import AddNewSourcesController  # type: ignore # noqa: F401
from bingr.controllers.channelsController import ChannelsController  # type: ignore # noqa: F401
from bingr.controllers.favoritesController import FavoritesController  # type: ignore # noqa: F401
from bingr.controllers.homeController import HomeController  # type: ignore # noqa: F401
from bingr.controllers.mainPlayerController import (  # type: ignore  # noqa: F401
    MainPlayerController,
    MpvFramebufferObject,
)
from bingr.controllers.settingsController import SettingsController  # type: ignore # noqa: F401
from bingr.controllers.splashScreenController import SplashScreenController  # type: ignore # noqa: F401
from bingr.controllers.statusBarController import StatusBarController  # type: ignore  # noqa: F401
from bingr.db.dbManager import DatabaseManager
from bingr.jobs.memoryTrimJob import MemoryTrimJob
from bingr.jobs.systemHealthMonitorJob import SystemHealthMonitorJob
from bingr.services.processM3UFilesService import M3UFilesProcessor  # type: ignore # noqa: F401
from bingr.services.systemHealthMonitorService import SystemHealthMonitorService  # type: ignore

# TODO: Re-enable reachability check job when a smarter probe strategy is designed.
# from bingr.jobs.reachabilityCheckJob import ReachabilityCheckJob

logger = logging.getLogger("bingr.main")

MAX_WAIT_TIME_SECONDS = 5.0
BACKGROUND_JOBS_START_DELAY_SECONDS = 10

_QT_MSG_LEVEL_MAP = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}

_qmlLogger = logging.getLogger("bingr.qml")


def _qtMessageHandler(msgType: QtMsgType, context, message):
    """Route QML console.log/warn/error and Qt internal messages into bingr.log."""
    level = _QT_MSG_LEVEL_MAP.get(msgType, logging.INFO)
    _qmlLogger.log(level, "%s", message)


_systemHealth: SystemHealthMonitorService | None = None

_activeJobs: list[Any] = []

projectRoot = Path(__file__).parent.parent.parent

if isNuitka():
    projectRoot = Path(__file__).parent

if TYPE_CHECKING:
    SplashScreenControllerType = Any
    StatusBarControllerType = Any
else:
    SplashScreenControllerType = "SplashScreenController"
    StatusBarControllerType = "StatusBarController"


def startJobs() -> None:
    """Start all periodic background jobs (schedulers only — they emit event bus signals).

    Jobs are stored in _activeJobs to keep them alive for the app lifetime;
    each job exposes stop() for graceful shutdown.
    """

    # _activeJobs.append(HeroChannelsPeriodicRefreshJob())
    # TODO: Re-enable when reachability probing strategy is revisited.
    # _activeJobs.append(ReachabilityCheckJob(ffprobePath=FFPROBE_PATH))
    _activeJobs.append(SystemHealthMonitorJob())
    _activeJobs.append(MemoryTrimJob())
    logger.info("All periodic jobs started.")


def stopJobs() -> None:
    """Gracefully stop all running jobs on app shutdown."""
    while _activeJobs:
        job = _activeJobs.pop()
        try:
            job.stop()
        except Exception as e:
            logger.warning("Error stopping job %s: %s", type(job).__name__, e)


async def bootApp(splashCtrl: SplashScreenControllerType, bootStart: float):
    if not splashCtrl:
        logger.critical("splashCtrl is not created — cannot boot.")
        sys.exit(-1)

    try:
        # sleep foa bit to let the splash screen render
        splashCtrl.publishProgressMsg("Starting application...")
        await asyncio.sleep(0.7)

        splashCtrl.publishProgressMsg("Loading application configurations.....")
        await asyncio.sleep(0.7)
        cfg = getConfig()

        splashCtrl.publishProgressMsg("Initializing system caches....")
        await asyncio.sleep(0.7)
        initCache(cfg)

        splashCtrl.publishProgressMsg("Preparing databases and sources....")
        await asyncio.sleep(0.7)

        dbPath = cfg.dbPath()
        dbPath.parent.mkdir(parents=True, exist_ok=True)
        DatabaseManager.initialize(str(dbPath))

        # statusCtrl: StatusBarControllerType = appEngine.singletonInstance("bingr.controllers", "StatusBarController")
        # _ac_mod.set_status_controller(statusCtrl)

        splashCtrl.publishProgressMsg("Starting health monitoring service....")
        await asyncio.sleep(0.7)

        # workspace = cfg.workspacePath()
        # runtime.systemHealthMonitorService = SystemHealthMonitorService(workspace)
        # runtime.systemHealthMonitorService.runAllChecksOnDemand()

        # Delay periodic jobs until the app has fully settled (1 minute)
        logger.info(
            "Periodic background scheduling will start in %s second(s)",
            BACKGROUND_JOBS_START_DELAY_SECONDS,
        )
        QTimer.singleShot(BACKGROUND_JOBS_START_DELAY_SECONDS * 1000, startJobs)
        splashCtrl.publishProgressMsg("Scheduling jobs....")
        await asyncio.sleep(0.7)

        splashCtrl.publishProgressMsg("Starting application interface...")

        elapsed = time.monotonic() - bootStart
        if elapsed < MAX_WAIT_TIME_SECONDS:
            await asyncio.sleep(MAX_WAIT_TIME_SECONDS - elapsed)

        # Main app window called form splash screen controller, so splash screen can close itself and load the main window
        logger.info("App Boot completed.")

    except Exception as e:
        splashCtrl.publishProgressMsg(f"Initialization failed: {e}")
        logger.critical("Failed to initialize: %s", e, exc_info=True)


def main() -> None:
    runtime.appGlobal = QGuiApplication(sys.argv)

    # Capture QML console.log/warn/error + Qt warnings into bingr.log. Must be
    # installed before any QML loads (splash screen below).
    qInstallMessageHandler(_qtMessageHandler)

    cfg = getConfig()  # noqa: F841
    setupLogging()

    async def _shutdownDb():
        logger.info("Shutting down database engine …")
        await DatabaseManager.shutdown()

    runtime.appGlobal.aboutToQuit.connect(lambda: asyncio.ensure_future(_shutdownDb()))
    runtime.appGlobal.aboutToQuit.connect(stopJobs)
    runtime.appGlobal.aboutToQuit.connect(trimHeap)

    appEngineLocal = QQmlApplicationEngine()

    if appEngineLocal:
        factory = AppNetworkAccessManagerFactory(enableCache=True)
        appEngineLocal.setNetworkAccessManagerFactory(factory)

        appEngineLocal.addImportPath(Path(__file__).resolve().parent)

        # Use setdefault so an already-set env (e.g. Flatpak finish-args
        # --env=QT_QUICK_CONTROLS_CONF=/app/share/bingr/) is not overridden.
        os.environ.setdefault("QT_QUICK_CONTROLS_CONF", str(projectRoot / "qtquickcontrols2.conf"))

        # Make appEngine available to _bootApp via closure
        runtime.appEngineGlobal = appEngineLocal
        runtime.appEngineGlobal.loadFromModule("ui", "SplashScreenLoader")

    if not runtime.appEngineGlobal or not runtime.appEngineGlobal.rootObjects():
        sys.exit(-1)

    QtAsyncio.run(quit_qapp=True, handle_sigint=True)


if __name__ == "__main__":
    main()
