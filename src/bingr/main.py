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
from bingr.common.cache import initialize as init_cache
from bingr.common.config import get_config
from bingr.common.constants import KEYS
from bingr.common.logging import setup_logging
from bingr.controllers.addNewSourcesController import AddNewSourcesController  # type: ignore # noqa: F401
from bingr.controllers.channelsController import ChannelsController  # type: ignore # noqa: F401
from bingr.controllers.splashScreenController import SplashScreenController  # type: ignore # noqa: F401
from bingr.controllers.statusBarController import StatusBarController  # type: ignore  # noqa: F401
from bingr.db.manager import DatabaseManager
from bingr.services.processM3UFilesService import M3UFilesProcessor  # type: ignore # noqa: F401
from bingr.services.systemHealthMonitorService import SystemHealthMonitorService  # type: ignore

logger = logging.getLogger(__name__)

MAX_WAIt_TIME_SECONDS = 4.0

_system_health: SystemHealthMonitorService | None = None

app_engine: QQmlApplicationEngine | None = None

project_root = Path(__file__).parent.parent.parent

if "__compiled__" in globals():
    project_root = Path(__file__).parent

if TYPE_CHECKING:
    SplashScreenControllerType = Any
    StatusBarControllerType = Any
else:
    SplashScreenControllerType = "SplashScreenController"
    StatusBarControllerType = "StatusBarController"


async def _boot_app(boot_start):
    splash_ctrl: SplashScreenControllerType = None
    if not app_engine:
        logger.critical("appEngine is not created — cannot boot.")
        return
    else:
        splash_ctrl: SplashScreenControllerType = app_engine.singletonInstance(
            "bingr.controllers", "SplashScreenController"
        )

    try:
        # sleep foa bit to let the splash screen render
        splash_ctrl.publishProgressMsg("Starting application...")
        await asyncio.sleep(0.5)

        splash_ctrl.publishProgressMsg("Loading application configurations.....")
        await asyncio.sleep(0.5)
        cfg = get_config()

        # splash_ctrl.publishProgressMsg("Setting  logging…")
        await asyncio.sleep(0.5)
        setup_logging()

        splash_ctrl.publishProgressMsg("Initializing system caches....")
        await asyncio.sleep(0.5)
        init_cache(cfg)

        splash_ctrl.publishProgressMsg("Preparing databases and sources....")
        await asyncio.sleep(0.5)

        db_path = cfg.get(KEYS.DB_PATH)
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            DatabaseManager.initialize(db_path)
        else:
            ws = cfg.get(KEYS.WORKSPACE_PATH)
            if ws:
                db_path = str(Path(ws) / "db" / "bingr.db")
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                DatabaseManager.initialize(db_path)

        status_ctrl: StatusBarControllerType = app_engine.singletonInstance(
            "bingr.controllers", "StatusBarController"
        )
        # _ac_mod.set_status_controller(status_ctrl)

        global _system_health
        workspace = cfg.get(KEYS.WORKSPACE_PATH) or project_root
        _system_health = SystemHealthMonitorService(app_engine, workspace)

        splash_ctrl.publishProgressMsg("Starting application interface...")

        elapsed = time.monotonic() - boot_start
        if elapsed < MAX_WAIt_TIME_SECONDS:
            await asyncio.sleep(4.0 - elapsed)

        app_engine.loadFromModule("ui", "App")

        # refresh the counts and start the timer to refresh them periodically
        status_ctrl.refreshCounts()
        status_ctrl.startCountTimer()

        for obj in app_engine.rootObjects():
            if obj.objectName() == "splashWindow":
                obj.close()  # type: ignore
                break

        _system_health.run_all_checkd_on_demand()

        logger.info("Bingr initialized successfully — ready")

    except Exception as e:
        splash_ctrl.publishProgressMsg(f"Initialization failed: {e}")
        logger.critical("Failed to initialize: %s", e, exc_info=True)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)

    async def _shutdown_db():
        logger.info("Shutting down database engine …")
        await DatabaseManager.shutdown()

    app.aboutToQuit.connect(lambda: asyncio.ensure_future(_shutdown_db()))

    app_engine = QQmlApplicationEngine()

    if app_engine:
        app_engine.addImportPath(Path(__file__).resolve().parent)

    os.environ["QT_QUICK_CONTROLS_CONF"] = str(project_root / "qtquickcontrols2.conf")

    if app_engine:
        app_engine.loadFromModule("ui", "Splashscreen")

    if not app_engine or not app_engine.rootObjects():
        sys.exit(-1)

    def _schedule_boot():
        asyncio.create_task(  # noqa: RUF006
            _boot_app(time.monotonic())
        )

    QTimer.singleShot(0, _schedule_boot)

    QtAsyncio.run(quit_qapp=True, handle_sigint=True)
