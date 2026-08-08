"""Settings service — wraps QSettings (INI file in the app config folder) for user settings persistence.

Storage for now: ``<projectRoot>/config/settings.conf`` (INI). A later iteration will
move to the platform-native QSettings default location (QStandardPaths).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QSettings, Slot
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "bingr.services"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

SETTINGS_FILE_NAME = "settings.conf"

# Default values for every supported setting key (group/key).
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

# Keys whose change takes effect only after an application restart
# (MPV init, DB open, Constants.qml / logging setup are startup-time).
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


def defaultSettingsPath() -> Path:
    """Return the INI storage path under the platform config dir (XDG-aware)."""
    from bingr.common.config import getConfig
    return getConfig().configDir() / SETTINGS_FILE_NAME


@QmlElement
class SettingsService(QObject):
    """Persistence facade over ``QSettings`` (INI format) with known defaults.

    Non-singleton: the SettingsController owns a single instance and exposes it
    to QML. Methods are ``@Slot``-decorated so the UI can reach the service
    directly through the controller's ``service`` property.
    """

    def __init__(self, parent: QObject | None = None, settingsPath: Path | str | None = None) -> None:
        super().__init__(parent)
        path = Path(settingsPath) if settingsPath else defaultSettingsPath()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = QSettings(str(path), QSettings.Format.IniFormat)

    @Slot(str, result=bool)
    def contains(self, key: str) -> bool:
        return self._settings.contains(key)

    @Slot(str, result="QVariant")
    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key``, falling back to default then the known default."""
        if self.contains(key):
            return self._settings.value(key)
        if key in DEFAULT_VALUES:
            return DEFAULT_VALUES[key]
        return default

    @Slot(str, "QVariant")
    def set(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)
        logger.debug("settings set %s = %r", key, value)

    @Slot(str, result=bool)
    def requiresRestart(self, key: str) -> bool:
        return key in RESTART_REQUIRED_KEYS

    @Slot()
    def resetToDefaults(self) -> None:
        """Clear all persisted keys so every lookup returns the known default."""
        self._settings.clear()
        self._settings.sync()
        logger.info("settings reset to defaults")
