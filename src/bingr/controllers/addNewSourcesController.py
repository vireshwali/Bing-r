"""QML bridge for adding M3U sources — validates file drops, runs import pipeline."""

from __future__ import annotations

import asyncio
import logging
import traceback
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtQml import QmlElement

from bingr.common.eventBus import appEventBus
from bingr.common.eventTypes import ReloadChannelsDataEvent
from bingr.common.exceptions import (
    InvalidM3UFileError,
    ProcessingError,
    SourceAlreadyImportedError,
    SourceFileNotFoundError,
)
from bingr.services import importerService
from bingr.services.auditService import AuditCategory, auditLog
from bingr.ui_models.sourcesProcessingStatusModel import SourcesProcessingStatusModel
from bingr.ui_models.sourcesProcessingStatusViewModel import SourcesProcessingStatusViewModel

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
class AddNewSourcesController(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._sourcesProcessingStatusViewModel = SourcesProcessingStatusViewModel(self)

    @Property(QObject, constant=True)
    def sourcesProcessingStatusViewModel(self) -> SourcesProcessingStatusViewModel:
        return self._sourcesProcessingStatusViewModel

    @Slot("QStringList")
    def processM3UFiles(self, fileUrls: list[str]):
        task = asyncio.ensure_future(self._processAll(list(fileUrls)))
        task.add_done_callback(lambda fut: self._publishReloadChannelsDataEvent())

    def _publishReloadChannelsDataEvent(self) -> None:
        """Emit ReloadChannelsDataEvent event after M3U import completes."""
        appEventBus.reloadChannelsData.emit(ReloadChannelsDataEvent(True))

    async def _processAll(self, urls: list[str]):  # noqa: C901
        total = len(urls)
        success = skipped = failed = 0
        importedSourceIds: list[int] = []

        if total > 0:
            sourcesList: list[SourcesProcessingStatusModel] = []
            for item in urls:
                if item.startswith(("http://", "https://")):
                    displayName = item
                else:
                    displayName = str(self._resolve(item).absolute())
                sourcesList.append(SourcesProcessingStatusModel(displayName, "Pending"))
            self._sourcesProcessingStatusViewModel.resetItems(sourcesList)

            self._publishProgress(f"Processing {total} stream sources...")
        else:
            self._publishProgress("No M3U sources received to process.")
            return

        for i, item in enumerate(urls, 1):
            if item.startswith(("http://", "https://")):
                if not self._isValidUrl(item):
                    failed += 1
                    self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Failed: Invalid URL")
                    self._publishProgress(f"Invalid URL: {item}")
                    await auditLog(AuditCategory.SOURCE_FAILED, f"Invalid URL: {item}", reason="invalid_url")
                    continue
                name = self._nameFromUrl(item)
                m3uPath = None
                m3uUrl = item
            else:
                path = self._resolve(item)
                try:
                    path = self._validatePath(path)
                except ProcessingError as e:
                    failed += 1
                    if isinstance(e, SourceFileNotFoundError):
                        status = "Failed: File missing"
                    elif isinstance(e, InvalidM3UFileError):
                        status = "Failed: Invalid file"
                    else:
                        status = "Failed: Source error"
                    self._sourcesProcessingStatusViewModel.updateItem(i - 1, status)
                    self._publishProgress(str(e))
                    await auditLog(AuditCategory.SOURCE_FAILED, str(e), reason=e.reason, details=e.details)
                    continue
                name = path.stem
                m3uPath = path
                m3uUrl = None

            self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Processing")
            self._publishProgress(f"Importing '{name}', channels source {i} of {total}.")

            try:
                source = await importerService.importM3u(sourceName=name, m3uPath=m3uPath, url=m3uUrl)
                success += 1
                importedSourceIds.append(source.id)
                self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Imported")
                self._publishProgress(f"Finished import of '{name}': {source.channel_count} channels")
                await auditLog(
                    AuditCategory.SOURCE_PROCESSED,
                    f"Imported {name}: {source.channel_count} channels",
                    details={
                        "source_id": source.id,
                        "name": name,
                        "channel_count": source.channel_count,
                    },
                )
            except SourceAlreadyImportedError as e:
                skipped += 1
                self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Skipped")
                self._publishProgress(f"Skipped '{name}': {e}")
                await auditLog(AuditCategory.SOURCE_SKIPPED, str(e), reason=e.reason)
            except ProcessingError as e:
                failed += 1
                self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Failed: Import error")
                self._publishProgress(f"Failed '{name}': {e}")
                await auditLog(AuditCategory.SOURCE_FAILED, str(e), reason=e.reason, details=e.details)
            except Exception as e:
                failed += 1
                self._sourcesProcessingStatusViewModel.updateItem(i - 1, "Failed: Unknown err")
                self._publishProgress(f"Failed '{name}': {e}")
                await auditLog(
                    AuditCategory.SOURCE_FAILED,
                    str(e),
                    details={"traceback": traceback.format_exc()},
                    reason=str(e),
                    shared=True,
                )

        parts = []
        if success:
            parts.append(f"{success} imported")
        if skipped:
            parts.append(f"{skipped} skipped")
        if failed:
            parts.append(f"{failed} failed")
        self._publishProgress(f"Done: {', '.join(parts)}" if parts else "Done: nothing to import")

        # TODO: Re-enable reachability probe trigger when the job is re-activated.
        # if success:
        #     channelIds = await self._channelIdsForSources(importedSourceIds)
        #     if channelIds:
        #         appEventBus.reachabilityCheckRequested.emit(channelIds)
        #     else:
        #         logger.info("AddNewSources: imported sources have no channels to probe")

    async def _channelIdsForSources(self, sourceIds: list[int]) -> list[int]:
        """Return the channel IDs linked to the given imported M3U sources."""
        from sqlalchemy import select

        from bingr.db.dbManager import DatabaseManager
        from bingr.db.models import M3UChannel

        sm = DatabaseManager.get_sessionmaker()
        async with sm() as session:
            stmt = select(M3UChannel.channel_id).where(M3UChannel.source_id.in_(sourceIds))
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    def _resolve(self, url: str) -> Path:
        qurl = QUrl(url)
        pathStr = qurl.toLocalFile() if qurl.isLocalFile() else url
        path = Path(pathStr).resolve()
        return path

    def _isValidUrl(self, urlStr: str) -> bool:
        from urllib.parse import urlparse

        try:
            result = urlparse(urlStr)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except Exception:
            return False

    def _nameFromUrl(self, urlStr: str) -> str:
        from urllib.parse import urlparse

        result = urlparse(urlStr)
        stem = Path(result.path).stem
        if stem:
            return stem
        return "playlist"

    def _validatePath(self, path: Path) -> Path:
        if not path.exists():
            raise SourceFileNotFoundError(path)
        if path.suffix.lower() not in (".m3u", ".m3u8"):
            raise InvalidM3UFileError(path.name, path.suffix)
        return path

    def _publishProgress(self, msg: str):
        appEventBus.statusBarProgressUpdate.emit(msg)
