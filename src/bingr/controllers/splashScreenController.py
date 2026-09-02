"""Splash screen controller — exposes init progress to QML."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtQml import QmlElement, QmlSingleton

# To be used on the @QmlElement decorator
# (QML_IMPORT_MINOR_VERSION is optional)
QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlSingleton
class SplashScreenController(QObject):
    """Qt property bag hooked into the QML splash screen.

    The ``progress`` property is writable from Python and automatically
    notifies QML bindings when it changes, so the splash can display
    live status messages such as "Loading database…".
    """

    # Argument is the name of the arg that we will use in QML connection
    progressMsg = Signal(str, arguments=["msg"])

    def publishProgressMsg(self, msg: str):
        if msg:
            self.progressMsg.emit(msg)
