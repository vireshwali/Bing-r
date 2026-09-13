from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from bingr.services.systemHealthMonitorService import SystemHealthMonitorService

# Convenient placehodlers for app wide usage
appGlobal: QGuiApplication | None = None
appEngineGlobal: QQmlApplicationEngine | None = None
systemHealthMonitorService: SystemHealthMonitorService | None = None
