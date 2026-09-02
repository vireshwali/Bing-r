"""DatabaseManager lifecycle edge cases — pre-init, double-init, shutdown."""

import pytest

from bingr.db.dbManager import DatabaseManager


class TestDatabaseManager:
    @pytest.fixture(autouse=True)
    def _reset(self):
        DatabaseManager._engine = None
        DatabaseManager._sessionmaker = None
        DatabaseManager._atexit = False
        yield

    def testGetSessionmakerRaisesBeforeInit(self):
        with pytest.raises(RuntimeError, match="not initialised"):
            DatabaseManager.get_sessionmaker()

    def testDoubleInitialize(self, tmp_path):
        db = tmp_path / "test.db"
        DatabaseManager.initialize(db)
        engine_1 = DatabaseManager._engine
        DatabaseManager.initialize(db)
        engine_2 = DatabaseManager._engine
        assert engine_1 is not engine_2

    def testShutdownSafeWithoutInit(self):
        DatabaseManager.shutdownSync()
