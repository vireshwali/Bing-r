"""Unit tests for SettingsService — DB-backed get/setBulk/loadAll/reset."""

import dataclasses

import pytest

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Settings
from bingr.services.settingsService import SettingsService
from bingr.ui_models.settigsModel import SettingsModel

_CREATE_SETTINGS_TABLE = """\
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value JSON,
    created_at TEXT,
    updated_at TEXT
)
"""


class TestSettingsService:
    @pytest.fixture(autouse=True)
    def _setupDb(self, tmp_path):
        dbPath = tmp_path / "settings_test.db"
        DatabaseManager._engine = None
        DatabaseManager._sessionmaker = None
        DatabaseManager.initialize(dbPath)
        # Create the settings table via raw SQL (no Alembic migration for it yet)
        import sqlite3

        conn = sqlite3.connect(str(dbPath))
        conn.execute(_CREATE_SETTINGS_TABLE)
        conn.commit()
        conn.close()
        self._service = SettingsService()
        yield
        DatabaseManager.shutdownSync()

    # ── get ────────────────────────────────────────────────────────────

    async def testGetUnknownKeyReturnsFieldDefault(self):
        value = await self._service.get("homeScreenContinueWatchingChannelsSize")
        assert value == SettingsModel.homeScreenContinueWatchingChannelsSize

    async def testGetUnknownKeyReturnsNoneForNonField(self):
        value = await self._service.get("no/such/key")
        assert value is None

    async def testGetStoredKeyReturnsStoredValue(self):
        model = SettingsModel(homeScreenContinueWatchingChannelsSize=20)
        await self._service.setBulk(model)
        value = await self._service.get("homeScreenContinueWatchingChannelsSize")
        assert value == 20

    # ── loadAll ────────────────────────────────────────────────────────

    async def testLoadAllEmptyDbReturnsDefaults(self):
        model = await self._service.loadAll()
        assert isinstance(model, SettingsModel)
        assert model.homeScreenContinueWatchingChannelsSize == 15
        assert model.hideNotWorkingChannelsWithOneFeed is False

    async def testLoadAllMergesStoredValues(self):
        model = SettingsModel(
            homeScreenContinueWatchingChannelsSize=22,
            hideNotWorkingChannelsWithOneFeed=True,
        )
        await self._service.setBulk(model)
        loaded = await self._service.loadAll()
        assert loaded.homeScreenContinueWatchingChannelsSize == 22
        assert loaded.hideNotWorkingChannelsWithOneFeed is True
        # Other fields stay at defaults
        assert loaded.homeScreenCategory1ChannelsSize == 15

    # ── setBulk ────────────────────────────────────────────────────────

    async def testSetBulkPersistsAllFields(self):
        model = SettingsModel(homeScreenCategory1ChannelsSize=12)
        await self._service.setBulk(model)
        value = await self._service.get("homeScreenCategory1ChannelsSize")
        assert value == 12

    async def testSetBulkReplacesPreviousValues(self):
        model1 = SettingsModel(homeScreenContinueWatchingChannelsSize=20)
        await self._service.setBulk(model1)
        model2 = SettingsModel(homeScreenContinueWatchingChannelsSize=8)
        await self._service.setBulk(model2)
        value = await self._service.get("homeScreenContinueWatchingChannelsSize")
        assert value == 8

    async def testSetBulkFieldCountMatchesModel(self):
        model = SettingsModel()
        await self._service.setBulk(model)
        expectedFields = len(dataclasses.fields(SettingsModel))
        from sqlalchemy import func, select

        async with self._service._sm() as session:
            count = (await session.execute(select(func.count()).select_from(Settings))).scalar_one()
        assert count == expectedFields

    # ── contains ───────────────────────────────────────────────────────

    async def testContainsFalseForEmptyDb(self):
        assert await self._service.contains("homeScreenContinueWatchingChannelsSize") is False

    async def testContainsTrueAfterSetBulk(self):
        model = SettingsModel()
        await self._service.setBulk(model)
        assert await self._service.contains("homeScreenContinueWatchingChannelsSize") is True

    # ── resetToDefaults ────────────────────────────────────────────────

    async def testResetToDefaultsClearsAll(self):
        model = SettingsModel(homeScreenContinueWatchingChannelsSize=99)
        await self._service.setBulk(model)
        await self._service.resetToDefaults()
        value = await self._service.get("homeScreenContinueWatchingChannelsSize")
        assert value == SettingsModel.homeScreenContinueWatchingChannelsSize

    async def testLoadAllAfterResetReturnsDefaults(self):
        model = SettingsModel(hideNotWorkingChannelsWithOneFeed=True)
        await self._service.setBulk(model)
        await self._service.resetToDefaults()
        loaded = await self._service.loadAll()
        assert loaded.hideNotWorkingChannelsWithOneFeed is False

    # ── requiresRestart ────────────────────────────────────────────────

    def testRequiresRestartTrueForKnownKey(self):
        assert self._service.requiresRestart("general/language") is True

    def testRequiresRestartFalseForUnknownKey(self):
        assert self._service.requiresRestart("playback/defaultVolume") is False
