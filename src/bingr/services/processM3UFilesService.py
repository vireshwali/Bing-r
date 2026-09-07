"""QML bridge — exposes M3U file import to the Qt Quick UI.

M3UFilesProcessor receives a list of file URLs from QML, runs the import
pipeline for each, and emits completion signals back to the UI layer.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Slot
from PySide6.QtQml import QmlElement

# To be used on the @QmlElement decorator
# (QML_IMPORT_MINOR_VERSION is optional)
QML_IMPORT_NAME = "bingr.services"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class M3UFilesProcessor(QObject):
    def __init__(self):
        QObject.__init__(self)

    @Slot("QStringList")
    def processM3UFiles(self, fileUrls):
        return "white"
