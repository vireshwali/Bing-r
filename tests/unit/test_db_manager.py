"""DatabaseManager lifecycle edge cases — pre-init, double-init, shutdown."""

import pytest
from sqlalchemy import text

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


class TestConnectionPragmas:
    async def testInitializeEnablesWalJournalMode(self, tmp_path):
        db = tmp_path / "wal.db"
        DatabaseManager.initialize(db)
        sm = DatabaseManager.get_sessionmaker()
        async with sm() as session:
            journalMode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
        assert journalMode == "wal"

    async def testInitializeSetsBusyTimeout(self, tmp_path):
        db = tmp_path / "busy.db"
        DatabaseManager.initialize(db)
        sm = DatabaseManager.get_sessionmaker()
        async with sm() as session:
            busyTimeout = (await session.execute(text("PRAGMA busy_timeout"))).scalar_one()
        assert busyTimeout >= 30000

    async def testEveryConnectionGetsThePragmas(self, tmp_path):
        db = tmp_path / "nullpool.db"
        DatabaseManager.initialize(db)
        sm = DatabaseManager.get_sessionmaker()
        for _ in range(2):
            async with sm() as session:
                journalMode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
                assert journalMode == "wal"
