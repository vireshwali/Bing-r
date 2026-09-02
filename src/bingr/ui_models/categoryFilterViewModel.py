from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    Property,
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
from bingr.ui_models.filterOptionModel import FilterOptionModel

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import ChannelsManagementService

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1

_INV_INDEX = QModelIndex()

logger = logging.getLogger(__name__)


@QmlElement
class CategoryFilterViewModel(QAbstractListModel):
    ValueRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2

    currentIndexChanged = Signal(int)
    isLoading = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[FilterOptionModel] = []
        self._currentIndex: int = 0
        self._service: ChannelsManagementService | None = None
        self._fetchTask: asyncio.Task[object] | None = None

        appEventBus.reloadChannelsData.connect(self.onReloadChannelsData)

    def setService(self, service: ChannelsManagementService) -> None:
        self._service = service
        self._fetch()

    @Property(int, notify=currentIndexChanged)
    def currentIndex(self) -> int:  # pyright: ignore[reportRedeclaration]
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, value: int) -> None:  # pyright: ignore[reportRedeclaration]
        if value != self._currentIndex:
            self._currentIndex = value
            self.currentIndexChanged.emit(value)
            logger.info("currentINdex is: %s", self._currentIndex)

    @Slot(object)
    def onReloadChannelsData(self, event: ReloadChannelsDataEvent) -> None:
        if event.doReload:
            saved = self._getSelectedValue()
            self._fetch(saved)

    def _fetch(self, savedValue: str = "all") -> None:
        if not self._service:
            return
        self.isLoading.emit(True)
        self._fetchTask = asyncio.ensure_future(self._doFetch(savedValue))

    async def _doFetch(self, savedValue: str) -> None:
        if not self._service:
            return
        try:
            names = await self._service.getDistinctCategories()
            if await self._service.hasUncategorizedChannels():
                names.append("Uncategorized")
                names.sort()
            items = [FilterOptionModel(value="all", text="All Categories")]
            items.extend(FilterOptionModel(value=n, text=n) for n in names)
            self._replaceItems(items, savedValue)
        except Exception as e:
            logger.exception("Failed to fetch categories: %s", e)
        finally:
            self.isLoading.emit(False)

    def _replaceItems(self, items: list[FilterOptionModel], savedValue: str) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        idx = next(
            (i for i, item in enumerate(self._items) if item.value == savedValue),
            0,
        )
        if idx != self._currentIndex:
            self._currentIndex = idx
            self.currentIndexChanged.emit(idx)

    def _getSelectedValue(self) -> str:
        if 0 <= self._currentIndex < len(self._items):
            return self._items[self._currentIndex].value
        return "all"

    @Property(str, notify=currentIndexChanged)
    def currentValue(self) -> str:
        return self._getSelectedValue()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INV_INDEX) -> int:
        return len(self._items)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == self.ValueRole:
            return item.value
        if role == self.TextRole:
            return item.text
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ValueRole: QByteArray(b"value"),
            self.TextRole: QByteArray(b"text"),
        }
