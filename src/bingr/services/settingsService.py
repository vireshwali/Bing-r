"""Settings service — persistence for the SettingsModel via the DB key-value store.

Uses the ``settings`` table (key/value with JSON values). Methods accept and
return ``SettingsModel`` instances; the DB keys are the dataclass field names.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Settings
from bingr.ui_models.settigsModel import SettingsModel

logger = logging.getLogger(__name__)


# ── Reference only — used to seed new settings when extending SettingsModel ──
# fmt: off
DEFAULT_VALUES: dict[str, Any] = {
    # ── General ─────────────────────────────────────────────────
    "general/language": "system",
    "general/theme": "system",
    "general/startMinimized": False,
    "general/confirmQuit": True,
    "general/checkUpdates": True,
    "general/workspacePath": "",
    # ── Playback ────────────────────────────────────────────────
    "playback/hwdec": "auto",
    "playback/gpuInterop": "auto",
    "playback/defaultVolume": 50,
    "playback/volumeStep": 5,
    "playback/bufferSeconds": 20,
    "playback/audioDelay": "auto",
    "playback/subtitlesEnabled": True,
    "playback/subtitleLanguage": "auto",
    "playback/audioLanguage": "auto",
    "playback/deinterlace": "auto",
    "playback/keepOpen": "onEof",
    # ── Network & Streaming ─────────────────────────────────────
    "network/downloadTimeout": 120,
    "network/userAgent": "Bingr/1.4",
    "network/proxyEnabled": False,
    "network/proxyUrl": "",
    "network/hlsLiveEdge": 3,
    "network/hlsSegmentThreads": 3,
    "network/diskCacheEnabled": True,
    "network/diskCacheSizeMB": 500,
    # ── Library & EPG ───────────────────────────────────────────
    "library/dbPath": "",
    "library/playlistsFolder": "",
    "library/autoScan": False,
    "library/epgFolder": "",
    "library/backupEnabled": True,
    "library/backupIntervalDays": 7,
    "library/backupKeep": 5,
    "epg/enabled": True,
    "epg/refreshIntervalHours": 12,
    "epg/customUrl": "",
    "epg/timezone": "local",
    "epg/showCurrent": True,
    "epg/showNext": True,
    # ── Appearance ──────────────────────────────────────────────
    "appearance/theme": "system",
    "appearance/accentColor": "blue",
    "appearance/fontSize": 13,
    "appearance/fontFamily": "system",
    "appearance/animationsEnabled": True,
    "appearance/animationSpeed": 1.0,
    "appearance/compactMode": False,
    "appearance/logoSize": "medium",
    "appearance/gridColumns": "auto",
    "appearance/showNumbers": True,
    "appearance/showGroup": True,
    "appearance/fsControlsTimeout": 3,
    # ── Privacy & Data ──────────────────────────────────────────
    "privacy/telemetryEnabled": False,
    "privacy/historyEnabled": True,
    "privacy/historyMaxEntries": 1000,
    "privacy/clearCacheOnExit": False,
    "privacy/crashReports": False,
    # ── Advanced ────────────────────────────────────────────────
    "advanced/logLevel": "info",
    "advanced/logToFile": False,
    "advanced/mpvLogLevel": "warn",
    "advanced/debugMpvProps": False,
    "advanced/experimental": False,
    "advanced/ffprobePath": "ffprobe",
    # ── Bingr-specific ──────────────────────────────────────────
    "bingr/heroAutoRefresh": True,
    "bingr/heroRefreshIntervalMin": 30,
    "bingr/enrichmentEnabled": True,
    "bingr/fuzzyThreshold": 0.85,
    "bingr/mergeDuplicates": True,
    "bingr/preferHd": True,
    "bingr/defaultSort": "name",
    "bingr/collapseGroups": False,
}
# fmt: on

# Keys whose change takes effect only after an application restart.
RESTART_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "general/language",
        "general/theme",
        "general/workspacePath",
        "playback/hwdec",
        "playback/gpuInterop",
        "library/dbPath",
        "appearance/theme",
        "appearance/accentColor",
        "appearance/fontSize",
        "appearance/fontFamily",
        "advanced/logLevel",
        "advanced/mpvLogLevel",
    }
)


def _fieldDefaults() -> dict[str, Any]:
    """Return ``{fieldName: defaultValue}`` for every field in SettingsModel."""
    return {f.name: f.default for f in dataclasses.fields(SettingsModel)}


class SettingsService:
    def __init__(self) -> None:
        self._sm: async_sessionmaker[AsyncSession] = DatabaseManager.get_sessionmaker()

    # ── Read ────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Any:
        """Return the stored value for *key*, or the ``SettingsModel`` field default."""
        defaults = _fieldDefaults()
        async with self._sm() as session:
            stmt = select(Settings.value).where(Settings.key == key)
            result = (await session.execute(stmt)).scalar_one_or_none()
        if result is not None:
            return result
        return defaults.get(key)

    async def loadAll(self) -> SettingsModel:
        """Return a ``SettingsModel`` populated from the DB (missing fields get defaults)."""
        async with self._sm() as session:
            stmt = select(Settings)
            rows = (await session.execute(stmt)).scalars().all()
        stored = {row.key: row.value for row in rows}
        defaults = _fieldDefaults()
        kwargs = {name: stored.get(name, defaults.get(name)) for name in defaults}
        return SettingsModel(**kwargs)

    # ── Write ───────────────────────────────────────────────────────────

    async def setBulk(self, model: SettingsModel) -> None:
        """Delete all settings and re-insert from *model* (full form submit)."""
        async with self._sm() as session:
            await session.execute(delete(Settings))
            for f in dataclasses.fields(model):
                session.add(Settings(key=f.name, value=getattr(model, f.name)))
            await session.commit()
        logger.info("settings: setBulk saved %d keys", len(dataclasses.fields(model)))

    # ── Utility ─────────────────────────────────────────────────────────

    async def contains(self, key: str) -> bool:
        """Return ``True`` if *key* exists in the DB."""
        async with self._sm() as session:
            stmt = select(Settings.key).where(Settings.key == key).limit(1)
            return (await session.execute(stmt)).scalar_one_or_none() is not None

    async def resetToDefaults(self) -> None:
        """Delete every row so all keys revert to ``SettingsModel`` defaults."""
        async with self._sm() as session:
            await session.execute(delete(Settings))
            await session.commit()
        logger.info("settings: reset to defaults")

    def requiresRestart(self, key: str) -> bool:
        """Return ``True`` if changing *key* needs an app restart."""
        return key in RESTART_REQUIRED_KEYS
