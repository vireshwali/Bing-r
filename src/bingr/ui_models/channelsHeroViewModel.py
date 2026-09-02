from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

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

_INV_INDEX = QModelIndex()

logger = logging.getLogger(__name__)


@QmlElement  # type: ignore[reportGeneralTypeIssues]
class ChannelsHeroViewModel(QAbstractListModel):
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
    VisitCountRole = Qt.ItemDataRole.UserRole + 16

    isLoading = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[ChannelDataModel] = []
        self._service: ChannelsManagementService | None = None
        self._fetchTask: asyncio.Task[object] | None = None

        appEventBus.reloadChannelsData.connect(self.onReloadHeroData)
        appEventBus.heroChannelsReloadRequested.connect(self.onHeroChannelsReloadRequested)

    def setService(self, service: ChannelsManagementService) -> None:
        self._service = service
        self._load()

    def _load(self) -> None:
        if not self._service:
            logger.warning("ChannelsHeroViewModel: no service injected")
            return
        self.isLoading.emit(True)
        self._fetchTask = asyncio.ensure_future(self._fetch())

    async def _fetch(self) -> None:
        if not self._service:
            return
        try:
            items = await self._service.getTopChannelsByVisitCount(limit=10)
            currentIds = [item.channelId for item in self._items]
            newIds = [item.channelId for item in items]
            if currentIds == newIds:
                logger.debug("Hero channels unchanged — discarding refresh")
                return
            self.beginResetModel()
            self._items = items
            self.endResetModel()
        except Exception as e:
            logger.exception("Failed to fetch hero channels: %s", e)
        finally:
            self.isLoading.emit(False)

    def resetItems(self, items: list[ChannelDataModel]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INV_INDEX) -> int:
        return len(self._items)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        return self._getItemValue(self._items[index.row()], role)

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
            self.VisitCountRole: "visitCount",
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
            self.VisitCountRole: QByteArray(b"visitCount"),
        }

    @Slot(object)
    def onReloadHeroData(self, event: ReloadChannelsDataEvent) -> None:
        logger.info("ReloadChannelsDataEvent received")
        if event.doReload:
            self._load()

    @Slot()
    def onHeroChannelsReloadRequested(self) -> None:
        logger.info("HeroChannelsReloadRequested received — reloading hero channels")
        self._load()
