"""Unit tests for the M3UFilesProcessor QML bridge.

The class is a thin Qt Quick bridge around the import pipeline; today it only
validates that it can be instantiated from QML and responds to the
``processM3UFiles`` slot.
"""

import pytest
from PySide6.QtCore import QCoreApplication

from bingr.services.processM3UFilesService import M3UFilesProcessor


@pytest.fixture(scope="module")
def qApp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


class TestM3UFilesProcessor:
    def testInstantiable(self, qApp):
        assert isinstance(M3UFilesProcessor(), M3UFilesProcessor)

    def testProcessM3UFilesAcceptsUrlList(self, qApp):
        processor = M3UFilesProcessor()
        assert processor.processM3UFiles(["file:///tmp/sample.m3u", "https://example.com/x.m3u8"]) == "white"

    def testProcessM3UFilesEmptyList(self, qApp):
        processor = M3UFilesProcessor()
        assert processor.processM3UFiles([]) == "white"
