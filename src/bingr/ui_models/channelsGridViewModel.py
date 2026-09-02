from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtQml import QmlElement

from bingr.common.eventBus import appEventBus
from bingr.common.eventTypes import ReloadChannelsDataEvent
from bingr.ui_models.channelDataModel import ChannelDataModel

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import ChannelsManagementService

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1

_INVALID_INDEX = QModelIndex()
PAGE_SIZE = 100
FIRST_PAGE_SIZE = PAGE_SIZE + 50

logger = logging.getLogger(__name__)


@QmlElement  # type: ignore[reportGeneralTypeIssues]
class ChannelsGridViewModel(QAbstractListModel):
    ChannelIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayNameRole = Qt.ItemDataRole.UserRole + 2
    LogoUrlRole = Qt.ItemDataRole.UserRole + 3
    CountryCodeRole = Qt.ItemDataRole.UserRole + 4
    CountryNameRole = Qt.ItemDataRole.UserRole + 5
    CategoryRole = Qt.ItemDataRole.UserRole + 6
    QualityRole = Qt.ItemDataRole.UserRole + 7
    ResolutionRole = Qt.ItemDataRole.UserRole + 8
    FeedCountRole = Qt.ItemDataRole.UserRole + 9
    IsFavoriteRole = Qt.ItemDataRole.UserRole + 10
    IsLiveRole = Qt.ItemDataRole.UserRole + 11
    WebsiteUrlRole = Qt.ItemDataRole.UserRole + 12
    LanguagesRole = Qt.ItemDataRole.UserRole + 13
    AltNamesRole = Qt.ItemDataRole.UserRole + 14
    AdditionalTagsRole = Qt.ItemDataRole.UserRole + 15

    isLoading = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[ChannelDataModel] = []

        self._offset: int = 0
        self._pageSize: int = PAGE_SIZE
        self._firstPageSize: int = FIRST_PAGE_SIZE
        self._hasMore: bool = True
        self._totalCount: int = 0
        self._filters: dict[str, Any] = {}
        self._service: ChannelsManagementService | None = None

        self._loading: bool = False
        self.isLoading.emit(False)
        self._fetchTask: asyncio.Task[Any] | None = None

        appEventBus.reloadChannelsData.connect(self.onReloadChannelsData)

    def setService(self, service: ChannelsManagementService) -> None:
        self._service = service

    def resetItems(self, items: list[ChannelDataModel]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def updateItem(self, row: int, **kwargs) -> None:
        if 0 <= row < len(self._items):
            item = self._items[row]
            changedRoles = []
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
                    role = getattr(self, f"{key[0].upper()}{key[1:]}Role", None)
                    if role:
                        changedRoles.append(role)
            if changedRoles:
                idx = self.index(row, 0)
                self.dataChanged.emit(idx, idx, changedRoles)

    def removeItem(self, row: int) -> None:
        if 0 <= row < len(self._items):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._items[row]
            self.endRemoveRows()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INVALID_INDEX) -> int:
        return len(self._items)

    def findChannelRow(self, channelId: int) -> int:
        """Return the row index of a channel, or -1 if it is not loaded."""
        for i, item in enumerate(self._items):
            if item.channelId == channelId:
                return i
        return -1

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        return self._getItemValue(item, role)

    def _getItemValue(self, item: ChannelDataModel, role: int) -> object | None:
        roleMap = {
            self.ChannelIdRole: "channelId",
            self.DisplayNameRole: "displayName",
            self.LogoUrlRole: "logoUrl",
            self.CountryCodeRole: "countryCode",
            self.CountryNameRole: "countryName",
            self.CategoryRole: "category",
            self.QualityRole: "quality",
            self.ResolutionRole: "resolution",
            self.FeedCountRole: "feedCount",
            self.IsFavoriteRole: "isFavorite",
            self.IsLiveRole: "isLive",
            self.WebsiteUrlRole: "websiteUrl",
            self.LanguagesRole: "languages",
            self.AltNamesRole: "altNames",
            self.AdditionalTagsRole: "additionalTags",
        }
        attr = roleMap.get(role)
        return getattr(item, attr, None) if attr else None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ChannelIdRole: QByteArray(b"channelId"),
            self.DisplayNameRole: QByteArray(b"displayName"),
            self.LogoUrlRole: QByteArray(b"logoUrl"),
            self.CountryCodeRole: QByteArray(b"countryCode"),
            self.CountryNameRole: QByteArray(b"countryName"),
            self.CategoryRole: QByteArray(b"category"),
            self.QualityRole: QByteArray(b"quality"),
            self.ResolutionRole: QByteArray(b"resolution"),
            self.FeedCountRole: QByteArray(b"feedCount"),
            self.IsFavoriteRole: QByteArray(b"isFavorite"),
            self.IsLiveRole: QByteArray(b"isLive"),
            self.WebsiteUrlRole: QByteArray(b"websiteUrl"),
            self.LanguagesRole: QByteArray(b"languages"),
            self.AltNamesRole: QByteArray(b"altNames"),
            self.AdditionalTagsRole: QByteArray(b"additionalTags"),
        }

    @Slot(object)
    def onReloadChannelsData(self, event: ReloadChannelsDataEvent) -> None:
        if event.doReload:
            self.reload()

    def canFetchMore(self, parent: QModelIndex | QPersistentModelIndex = _INVALID_INDEX) -> bool:
        return self._hasMore and not self._loading

    def fetchMore(self, parent: QModelIndex | QPersistentModelIndex = _INVALID_INDEX) -> None:
        if not self.canFetchMore():
            return
        self._loading = True
        self._loadPage()

    def _loadPage(self) -> None:
        self.isLoading.emit(True)
        self._fetchTask = asyncio.ensure_future(self._fetchPage())
        self._fetchTask.add_done_callback(
            lambda fut: (
                logger.info("Loading channels data page completed."),
                self.isLoading.emit(False),
            )
        )

    async def _fetchPage(self) -> None:
        if self._service is None:
            self._loading = False
            return

        limit = self._firstPageSize if self._offset == 0 else self._pageSize
        try:
            items = await self._service.getChannelsPage(self._offset, limit, self._filters)
            if not items:
                self._hasMore = False
            else:
                start = len(self._items)
                end = start + len(items) - 1
                self.beginInsertRows(QModelIndex(), start, end)
                self._items.extend(items)
                self.endInsertRows()
                self._offset += len(items)

            if len(items) < (self._firstPageSize if self._offset == 0 else self._pageSize):
                self._hasMore = False
        except Exception as e:
            logger.exception("Failed to fetch channels page: %s", e)
        finally:
            self._loading = False

    def _resetPaginationAndItems(self) -> None:
        self._offset = 0
        self._hasMore = True
        self._loading = False
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def reload(self) -> None:
        self._resetPaginationAndItems()
        self.fetchMore()

    def setFilters(self, **filters) -> None:
        self._filters = filters
        self._resetPaginationAndItems()
        self.fetchMore()
