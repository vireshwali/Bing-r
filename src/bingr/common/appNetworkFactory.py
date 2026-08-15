import logging

from PySide6.QtCore import QStandardPaths
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache
from PySide6.QtQml import QQmlNetworkAccessManagerFactory

logger = logging.getLogger(__name__)


class AppNetworkAccessManagerFactory(QQmlNetworkAccessManagerFactory):
    def create(self, parent):
        # Create the standard network manager
        manager = QNetworkAccessManager(parent)

        # Create a disk-backed cache to keep memory low
        disk_cache = QNetworkDiskCache(manager)

        # Set a safe path on the user's system
        logger.info(
            "Setting network disk cache path to: %s",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) + "/logo_cache",
        )
        cache_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) + "/logo_cache"
        disk_cache.setCacheDirectory(cache_path)

        # Strictly cap the cache size (e.g., 20 MB max)
        disk_cache.setMaximumCacheSize(20 * 1024 * 1024)

        # Apply cache to manager
        manager.setCache(disk_cache)
        return manager
