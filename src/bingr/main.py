"""Application entry point — boots the Qt Quick UI.

Sets QT_QUICK_CONTROLS_CONF, shows splash screen, initialises infra
asynchronously, then transitions to App.qml with a minimum 3s splash.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from bingr import qml_resources  # type: ignore # noqa: F401
from bingr.common.cache import initialize as initCache
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
from bingr.jobs.heroChannelsPeriodicRefreshJob import HeroChannelsPeriodicRefreshJob
from bingr.services.processM3UFilesService import M3UFilesProcessor  # type: ignore # noqa: F401
from bingr.services.systemHealthMonitorService import SystemHealthMonitorService  # type: ignore

logger = logging.getLogger("bingr.main")

MAX_WAIT_TIME_SECONDS = 4.0
BACKGROUND_JOBS_START_DELAY_MINUTES = 1

_systemHealth: SystemHealthMonitorService | None = None

_activeJobs: list[Any] = []

appEngine: QQmlApplicationEngine | None = None

projectRoot = Path(__file__).parent.parent.parent

if "__compiled__" in globals():
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

    _activeJobs.append(HeroChannelsPeriodicRefreshJob())
    logger.info("All periodic jobs started.")


def stopJobs() -> None:
    """Gracefully stop all running jobs on app shutdown."""
    while _activeJobs:
        job = _activeJobs.pop()
        try:
            job.stop()
        except Exception as e:
            logger.warning("Error stopping job %s: %s", type(job).__name__, e)


async def _bootApp(bootStart):
    splashCtrl: SplashScreenControllerType = None
    if not appEngine:
        logger.critical("appEngine is not created — cannot boot.")
        return
    else:
        splashCtrl: SplashScreenControllerType = appEngine.singletonInstance(
            "bingr.controllers", "SplashScreenController"
        )

    try:
        # sleep foa bit to let the splash screen render
        splashCtrl.publishProgressMsg("Starting application...")
        await asyncio.sleep(0.5)

        splashCtrl.publishProgressMsg("Loading application configurations.....")
        await asyncio.sleep(0.5)
        cfg = getConfig()

        # splashCtrl.publishProgressMsg("Setting  logging…")
        await asyncio.sleep(0.5)
        setupLogging()

        splashCtrl.publishProgressMsg("Initializing system caches....")
        await asyncio.sleep(0.5)
        initCache(cfg)

        splashCtrl.publishProgressMsg("Preparing databases and sources....")
        await asyncio.sleep(0.5)

        dbPath = cfg.dbPath()
        dbPath.parent.mkdir(parents=True, exist_ok=True)
        DatabaseManager.initialize(str(dbPath))

        statusCtrl: StatusBarControllerType = appEngine.singletonInstance("bingr.controllers", "StatusBarController")
        # _ac_mod.set_status_controller(statusCtrl)

        global _systemHealth
        workspace = cfg.workspacePath()
        _systemHealth = SystemHealthMonitorService(appEngine, workspace)

        splashCtrl.publishProgressMsg("Starting application interface...")

        elapsed = time.monotonic() - bootStart
        if elapsed < MAX_WAIT_TIME_SECONDS:
            await asyncio.sleep(4.0 - elapsed)

        appEngine.loadFromModule("ui", "App")

        # refresh the counts and start the timer to refresh them periodically
        statusCtrl.refreshCounts()
        statusCtrl.startCountTimer()

        for obj in appEngine.rootObjects():
            if obj.objectName() == "splashWindow":
                obj.close()  # type: ignore
                break

        _systemHealth.runAllChecksOnDemand()

        # Delay periodic jobs until the app has fully settled (1 minute)
        logger.info(
            "Periodic background scheduling will start in %s minute(s)",
            BACKGROUND_JOBS_START_DELAY_MINUTES,
        )
        QTimer.singleShot(BACKGROUND_JOBS_START_DELAY_MINUTES * 60 * 1000, startJobs)

        logger.info("Bingr initialized successfully — ready")

    except Exception as e:
        splashCtrl.publishProgressMsg(f"Initialization failed: {e}")
        logger.critical("Failed to initialize: %s", e, exc_info=True)


def main() -> None:
    """Application entry point — can be called from gui-scripts or __main__."""
    app = QGuiApplication(sys.argv)
    cfg = getConfig()  # noqa: F841

    async def _shutdownDb():
        logger.info("Shutting down database engine …")
        await DatabaseManager.shutdown()

    app.aboutToQuit.connect(lambda: asyncio.ensure_future(_shutdownDb()))
    app.aboutToQuit.connect(stopJobs)

    appEngineLocal = QQmlApplicationEngine()

    if appEngineLocal:
        appEngineLocal.addImportPath(Path(__file__).resolve().parent)

    # Use setdefault so an already-set env (e.g. Flatpak finish-args
    # --env=QT_QUICK_CONTROLS_CONF=/app/share/bingr/) is not overridden.
    os.environ.setdefault("QT_QUICK_CONTROLS_CONF", str(projectRoot / "qtquickcontrols2.conf"))

    if appEngineLocal:
        appEngineLocal.loadFromModule("ui", "SplashScreen")

    if not appEngineLocal or not appEngineLocal.rootObjects():
        sys.exit(-1)

    # Make appEngine available to _bootApp via closure
    global appEngine
    appEngine = appEngineLocal

    def _scheduleBoot():
        asyncio.create_task(  # noqa: RUF006
            _bootApp(time.monotonic())
        )

    QTimer.singleShot(0, _scheduleBoot)

    QtAsyncio.run(quit_qapp=True, handle_sigint=True)


if __name__ == "__main__":
    main()
