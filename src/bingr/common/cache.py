"""App-wide cache singletons: MemoryCache (in-memory TTL) and FileDataCache (file-backed JSON)."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

import httpx
import orjson  # pyright: ignore[reportMissingModuleSource]

from bingr.common.config import get_config
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
    def _api_dir(self) -> Path:
        return get_config().get(KEYS.WORKSPACE_PATH) / "api"

    @property
    def _ttl_days(self) -> int:
        return get_config().get_int(KEYS.FILE_CACHE_TTL, 7)

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
        local_name, url = API_FILES[name]
        path = self._api_dir / local_name
        if path.exists():
            age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
            if age < timedelta(days=self._ttl_days):
                logger.debug("cache fresh: %s (%s old)", local_name, age)
                return
            logger.info("cache stale: %s (%s old)", local_name, age)
        self._download(url, path)

    def ensure_all(self):
        """Ensure every known API file is cached on disk."""
        for name in API_FILES:
            self.ensure(name)

    def load(self, name: str) -> list[dict[str, Any]]:
        """Return parsed JSON data for *name*, from memory → disk → download."""
        if name in self._store:
            logger.debug("cache hit: %s (%d records)", name, len(self._store[name]))
            return self._store[name]

        local_name = API_FILES[name][0]
        path = self._api_dir / local_name
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
        logger.debug("loaded %s: %d records", local_name, len(data))
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
    api_dir = cfg.get(KEYS.WORKSPACE_PATH) / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    get_memory_cache()
    get_file_cache()
    _initialized = True
    logger.info("Cache initialized — memory + file (%s)", api_dir)


# ── singleton accessors ──────────────────────────────────────────

_file_cache: FileDataCache | None = None
_memory_cache: MemoryCache | None = None


def get_file_cache() -> FileDataCache:
    global _file_cache
    if _file_cache is None:
        _file_cache = FileDataCache()
    return _file_cache


def get_memory_cache(ttl: int = 300) -> MemoryCache:
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = MemoryCache(ttl=ttl)
    return _memory_cache
