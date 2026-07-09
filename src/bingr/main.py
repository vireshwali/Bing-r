#!/usr/bin/env python3

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

app = QGuiApplication(sys.argv)

engine = QQmlApplicationEngine()
engine.load(Path(__file__).parent / "ui" / "App.qml")

sys.exit(app.exec())
