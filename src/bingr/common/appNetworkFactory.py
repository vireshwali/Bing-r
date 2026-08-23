"""Shared factory for Qt ``QNetworkAccessManager`` instances.

The whole app creates network managers through ``AppNetworkAccessManagerFactory``
so connection policy, caching and memory behaviour live in one place. The QML
engine uses an instance with caching enabled (logo/image loading benefits from
a disk cache); background services (HTTP probing, stream checks) use a bare
instance — no ``QNetworkDiskCache``, no cache memory, no disk I/O.
"""

import logging

from PySide6.QtCore import QStandardPaths
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache
from PySide6.QtQml import QQmlNetworkAccessManagerFactory

logger = logging.getLogger(__name__)

NETWORK_CACHE_MAX_BYTES = 50 * 1024 * 1024


class AppNetworkAccessManagerFactory(QQmlNetworkAccessManagerFactory):
    """Create network managers with a configurable cache.

    ``enableCache=False`` (default) returns a bare manager — the memory-light
    choice for probes and jobs. ``enableCache=True`` attaches a disk-backed
    ``QNetworkDiskCache`` capped at ``NETWORK_CACHE_MAX_BYTES``, for the QML
    engine which loads remote images.
    """

    def __init__(self, enableCache: bool = False):
        super().__init__()
        self._enableCache = enableCache

    def create(self, parent):
        manager = QNetworkAccessManager(parent)

        if not self._enableCache:
            return manager

        disk_cache = QNetworkDiskCache(manager)
        cache_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) + "/network_cache"
        logger.info("Setting network disk cache path to: %s", cache_path)
        disk_cache.setCacheDirectory(cache_path)
        disk_cache.setMaximumCacheSize(NETWORK_CACHE_MAX_BYTES)
        manager.setCache(disk_cache)
        return manager
