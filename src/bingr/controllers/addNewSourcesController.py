"""QML bridge for adding M3U sources — validates file drops, runs import pipeline."""

from __future__ import annotations

import asyncio
import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtQml import QmlElement, QQmlEngine, qmlEngine

from bingr.common.eventBus import appEventBus
from bingr.common.eventTypes import ReloadChannelsDataEvent
from bingr.common.exceptions import (
    InvalidM3UFileError,
    ProcessingError,
    SourceAlreadyImportedError,
    SourceFileNotFoundError,
)
from bingr.services import importerService
from bingr.services.auditService import AuditCategory, audit_log
from bingr.ui_models.sourcesProcessingStatusModel import SourcesProcessingStatusModel
from bingr.ui_models.sourcesProcessingStatusViewModel import SourcesProcessingStatusViewModel

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


# If type checking, treat it as Any to bypass the error, but use it as a string literal
if TYPE_CHECKING:
    StatusBarControllerType = Any
else:
    StatusBarControllerType = "StatusBarController"


@QmlElement
class AddNewSourcesController(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.app_engine: QQmlEngine | None = qmlEngine(self)
        self._sourcesProcessingStatusViewModel = SourcesProcessingStatusViewModel(self)

    @Property(QObject, constant=True)
    def sourcesProcessingStatusViewModel(self) -> SourcesProcessingStatusViewModel:
        return self._sourcesProcessingStatusViewModel

    @Slot("QStringList")
    def processM3UFiles(self, fileUrls: list[str]):
        task = asyncio.ensure_future(self._process_all(list(fileUrls)))
        task.add_done_callback(lambda fut: self._publishReloadChannelsDataEvent())

    def _publishReloadChannelsDataEvent(self) -> None:
        """Emit ReloadChannelsDataEvent event after M3U import completes."""
        appEventBus.reloadChannelsData.emit(ReloadChannelsDataEvent(True))
        logger.info("ReloadChannelsDataEvent emitted")

    async def _process_all(self, urls: list[str]):  # noqa: C901
        total = len(urls)
        success = skipped = failed = 0

        _status_ctrl: StatusBarControllerType | None

        if self.app_engine:
            _status_ctrl = self.app_engine.singletonInstance("bingr.controllers", "StatusBarController")
        else:
            # sometimes it might happen that this instance may not have the app egine available,
            # in that case we can try to get it from the qmlEngine again
            self.app_engine = qmlEngine(self)

            # if its still not available, we can log an error else get the status controller from the app engine
            if not self.app_engine:
                raise RuntimeError("AddNewSourcesController: app_engine is not available, cannot process sources.")
            else:
                _status_ctrl = self.app_engine.singletonInstance("bingr.controllers", "StatusBarController")

        if total > 0:
            sourcesList: list[SourcesProcessingStatusModel] = []
            for item in urls:
                if item.startswith(("http://", "https://")):
                    display_name = item
                else:
                    display_name = str(self._resolve(item).absolute())
                sourcesList.append(SourcesProcessingStatusModel(display_name, "Pending"))
            self._sourcesProcessingStatusViewModel.ResetItems(sourcesList)

            self._publishMsg(_status_ctrl, f"Processing {total} stream sources...")
        else:
            self._publishMsg(_status_ctrl, "No M3U sources received to process.")
            return

        for i, item in enumerate(urls, 1):
            if item.startswith(("http://", "https://")):
                if not self._is_valid_url(item):
                    failed += 1
                    self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Failed: Invalid URL")
                    self._publishMsg(_status_ctrl, f"Invalid URL: {item}")
                    await audit_log(AuditCategory.SOURCE_FAILED, f"Invalid URL: {item}", reason="invalid_url")
                    continue
                name = self._name_from_url(item)
                m3u_path = None
                m3u_url = item
            else:
                path = self._resolve(item)
                try:
                    path = self._validate_path(path)
                except ProcessingError as e:
                    failed += 1
                    if isinstance(e, SourceFileNotFoundError):
                        status = "Failed: File missing"
                    elif isinstance(e, InvalidM3UFileError):
                        status = "Failed: Invalid file"
                    else:
                        status = "Failed: Source error"
                    self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, status)
                    self._publishMsg(_status_ctrl, str(e))
                    await audit_log(AuditCategory.SOURCE_FAILED, str(e), reason=e.reason, details=e.details)
                    continue
                name = path.stem
                m3u_path = path
                m3u_url = None

            self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Processing")
            self._publishMsg(_status_ctrl, f"Starting import of {name}, channels source {i} of {total}.")

            try:
                source = await importerService.import_m3u(source_name=name, m3u_path=m3u_path, url=m3u_url)
                success += 1
                self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Imported")
                self._publishMsg(_status_ctrl, f"Imported '{name}': {source.channel_count} channels")
                await audit_log(
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
                self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Skipped")
                self._publishMsg(_status_ctrl, f"Skipped '{name}': {e}")
                await audit_log(AuditCategory.SOURCE_SKIPPED, str(e), reason=e.reason)
            except ProcessingError as e:
                failed += 1
                self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Failed: Import error")
                self._publishMsg(_status_ctrl, f"Failed '{name}': {e}")
                await audit_log(AuditCategory.SOURCE_FAILED, str(e), reason=e.reason, details=e.details)
            except Exception as e:
                failed += 1
                self._sourcesProcessingStatusViewModel.UpdateItem(i - 1, "Failed: Unknown err")
                self._publishMsg(_status_ctrl, f"Failed '{name}': {e}")
                await audit_log(
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
        self._publishMsg(_status_ctrl, f"Done: {', '.join(parts)}" if parts else "Done: nothing to import")

    def _resolve(self, url: str) -> Path:
        qurl = QUrl(url)
        path_str = qurl.toLocalFile() if qurl.isLocalFile() else url
        path = Path(path_str).resolve()
        return path

    def _is_valid_url(self, url_str: str) -> bool:
        from urllib.parse import urlparse

        try:
            result = urlparse(url_str)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except Exception:
            return False

    def _name_from_url(self, url_str: str) -> str:
        from urllib.parse import urlparse

        result = urlparse(url_str)
        stem = Path(result.path).stem
        if stem:
            return stem
        return "playlist"

    def _validate_path(self, path: Path) -> Path:
        if not path.exists():
            raise SourceFileNotFoundError(path)
        if path.suffix.lower() not in (".m3u", ".m3u8"):
            raise InvalidM3UFileError(path.name, path.suffix)
        return path

    def _publishMsg(self, _status_ctrl: StatusBarControllerType, msg: str):
        if _status_ctrl:
            _status_ctrl.publishProgress(msg)
        logger.info("%s", msg)
