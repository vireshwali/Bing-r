"""App configuration — singleton Config, dotenv loading, and type inference.

Config loads .env files (shipped + user + env vars) and provides typed accessors
(get, getInt, getBool). _infer() converts raw strings to bool/int/float/Path.
getConfig() returns the lazily-initialised singleton Config.
"""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key

from bingr.common.commonUtils import isFlatpak, isNuitka

logger = logging.getLogger(__name__)


def _infer(raw: str) -> Any:
    lr = raw.lower()
    if lr in ("true", "false"):
        return lr == "true"
    if raw.startswith("~") or raw.startswith("/"):
        return Path(raw).expanduser()
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# ── XDG / path resolution ──────────────────────────────────────────


def _xdgConfigHome() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdgDataHome() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _projectRoot() -> Path:
    """Fallback for local dev: four levels up from this file (src/bingr/common/config.py)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _getDefaultDotenvLocations() -> list[Path]:
    """User-level .env locations — XDG-aware (works in Flatpak and local dev)."""
    return [_xdgConfigHome() / "Bing-r" / ".env"]


def _resolveShippedDotenv() -> Path | None:
    """Locate the shipped .env. Returns None in Flatpak (not installed there;
    all defaults live as ``get(key, default)`` fallbacks in code)."""
    if isFlatpak():
        return None
    return Path(__file__).resolve().parent.parent.parent.parent / "config" / ".env"


class Config:
    __slots__ = ("_dotenvPaths", "_store")

    def __init__(self, dotenvPath: str | Path | None = None):
        self._store: dict[str, str] = {}
        self._dotenvPaths: list[Path] = []

        shipped = _resolveShippedDotenv()
        if shipped is not None:
            self._loadOne(shipped)

        for p in _getDefaultDotenvLocations():
            if p.exists():
                self._loadOne(p)

        if dotenvPath:
            p = Path(dotenvPath).expanduser()
            if p.exists():
                self._loadOne(p)

        for key, val in os.environ.items():
            if "." in key and val:
                self._store[key] = val

    def _loadOne(self, path: Path) -> None:
        values = dotenv_values(str(path))
        for key, val in values.items():
            if val is not None:
                self._store[key] = val
        self._dotenvPaths.append(path)

    def configDir(self) -> Path:
        """Directory for config files (.env, settings)."""
        if isFlatpak() or isNuitka():
            return _xdgConfigHome() / "Bing-r"
        return _projectRoot() / "config"

    def dataDir(self) -> Path:
        """Directory for persistent data (DB, API cache, playlists)."""
        if isFlatpak() or isNuitka():
            return _xdgDataHome() / "bingr"
        return _projectRoot() / "workspace"

    def logDir(self) -> Path:
        """Directory for log files."""
        if isFlatpak() or isNuitka():
            return _xdgDataHome() / "bingr" / "logs"
        return _projectRoot() / "logs"

    def dbPath(self) -> Path:
        """Full path to the SQLite database file."""
        dbName = self.get("db.name", "bingr.db")
        return self.dataDir() / "db" / dbName

    def workspacePath(self) -> Path:
        """Alias for dataDir — root of all app data."""
        return self.dataDir()

    def get(self, key: str, default: Any = None) -> Any:
        raw = self._store.get(key, "")
        if not raw:
            return default
        return _infer(raw)

    def getInt(self, key: str, default: int = 0) -> int:
        raw = self._store.get(key, "")
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "Config key %r has non-integer value %r — returning default %d",
                key,
                raw,
                default,
                exc_info=True,
            )
            return default

    def getBool(self, key: str, default: bool = False) -> bool:
        raw = self._store.get(key, "").lower()
        if raw == "true":
            return True
        if raw == "false":
            return False
        if raw:
            logger.warning(
                "Config key %r has non-boolean value %r — returning default %s",
                key,
                raw,
                default,
            )
        return default

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        self._store[key] = str(value)
        if persist and self._dotenvPaths:
            set_key(str(self._dotenvPaths[-1]), key, str(value))


_configInstance: Config | None = None


def getConfig(dotenvPath: str | Path | None = None) -> Config:
    global _configInstance
    if _configInstance is None:
        _configInstance = Config(dotenvPath)
    return _configInstance
