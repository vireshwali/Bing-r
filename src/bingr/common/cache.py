"""App-wide cache singletons: MemoryCache (in-memory TTL) and FileDataCache (file-backed JSON)."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

import httpx
import orjson  # pyright: ignore[reportMissingModuleSource]

from bingr.common.config import getConfig
from bingr.common.constants import API_FILES, KEYS

logger = logging.getLogger(__name__)


class MemoryCache:
    """In-memory key-value cache with TTL expiry."""

    __slots__ = ("_store", "_ttl")

    def __init__(self, ttl: int | float = 300):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        if self._ttl <= 0:
            return None
        expires, val = self._store.get(key, (0, None))
        if expires == 0:
            return None
        if monotonic() > expires:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        if self._ttl > 0:
            self._store[key] = (monotonic() + self._ttl, val)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class FileDataCache:
    """File-backed + in-memory cache for iptv-org API JSON data.

    On ``load(name)`` the cache checks:
      1. in-memory ``_store``
      2. file on disk under ``<workspace>/api/``
      3. downloads from iptv-org if file missing or stale
    """

    def __init__(self):
        self._store: dict[str, list[dict[str, Any]]] = {}

    @property
    def _apiDir(self) -> Path:
        return getConfig().workspacePath() / "api"

    @property
    def _ttlDays(self) -> int:
        return getConfig().getInt(KEYS.FILE_CACHE_TTL, 7)

    # ── internal helpers ────────────────────────────────────────

    def _download(self, url: str, path: Path):
        logger.info("downloading %s ...", path.name)
        try:
            with httpx.Client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
            logger.info("  %s: %s bytes", path.name, path.stat().st_size)
        except Exception as e:
            logger.error("failed to download %s from %s: %s", path.name, url, e)
            raise

    # ── public API ──────────────────────────────────────────────

    def ensure(self, name: str):
        """Download the API file *name* if it is missing or stale on disk."""
        localName, url = API_FILES[name]
        path = self._apiDir / localName
        if path.exists():
            age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
            if age < timedelta(days=self._ttlDays):
                logger.debug("cache fresh: %s (%s old)", localName, age)
                return
            logger.info("cache stale: %s (%s old)", localName, age)
        self._download(url, path)

    def ensureAll(self):
        """Ensure every known API file is cached on disk."""
        for name in API_FILES:
            self.ensure(name)

    def load(self, name: str) -> list[dict[str, Any]]:
        """Return parsed JSON data for *name*, from memory → disk → download."""
        if name in self._store:
            logger.debug("cache hit: %s (%d records)", name, len(self._store[name]))
            return self._store[name]

        localName = API_FILES[name][0]
        path = self._apiDir / localName
        if not path.exists():
            logger.warning("cache file not found: %s (returning [] for %s)", path, name)
            self._store[name] = []
            return []

        try:
            with open(path, "rb") as f:
                data = orjson.loads(f.read())
        except (orjson.JSONDecodeError, OSError) as e:
            logger.error("failed to load %s: %s (returning [])", path, e)
            self._store[name] = []
            return []

        self._store[name] = data
        logger.debug("loaded %s: %d records", localName, len(data))
        return data

    def clear(self):
        """Clear the in-memory cache. Next load() re-reads from disk."""
        self._store.clear()


# ── bootstrap ─────────────────────────────────────────────────

_initialized: bool = False


def initialize(cfg: Any) -> None:
    """Create all cache singletons and ensure their backing directories exist.

    Must be called once at app startup (or in test fixtures) after config
    has been loaded.  Safe to call multiple times — subsequent calls are
    no-ops.
    """
    global _initialized
    if _initialized:
        return
    apiDir = cfg.workspacePath() / "api"
    apiDir.mkdir(parents=True, exist_ok=True)
    getMemoryCache()
    getFileCache()
    _initialized = True
    logger.info("Cache initialized — memory + file (%s)", apiDir)


# ── singleton accessors ──────────────────────────────────────────

_fileCache: FileDataCache | None = None
_memoryCache: MemoryCache | None = None


def getFileCache() -> FileDataCache:
    global _fileCache
    if _fileCache is None:
        _fileCache = FileDataCache()
    return _fileCache


def getMemoryCache(ttl: int = 300) -> MemoryCache:
    global _memoryCache
    if _memoryCache is None:
        _memoryCache = MemoryCache(ttl=ttl)
    return _memoryCache
