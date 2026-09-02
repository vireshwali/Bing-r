from __future__ import annotations

import logging

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
)
from PySide6.QtQml import QmlElement

from bingr.ui_models.filterOptionModel import FilterOptionModel

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1

_INV_INDEX = QModelIndex()

_QUALITIES: list[str] = ["SD", "HD", "FHD", "4K", "8K"]

logger = logging.getLogger(__name__)


@QmlElement
class QualityFilterViewModel(QAbstractListModel):
    ValueRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2

    currentIndexChanged = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._currentIndex: int = 0
        self._buildItems()

    def setService(self, service: object = None) -> None:
        # No DB dependency - data is hardcoded
        pass

    def _buildItems(self) -> None:
        self._items: list[FilterOptionModel] = [
            FilterOptionModel(value="all", text="All Qualities"),
        ]
        self._items.extend(FilterOptionModel(value=q, text=q) for q in _QUALITIES)

    def _getSelectedValue(self) -> str:
        if 0 <= self._currentIndex < len(self._items):
            return self._items[self._currentIndex].value
        return "all"

    @Property(int, notify=currentIndexChanged)
    def currentIndex(self) -> int:  # pyright: ignore[reportRedeclaration]
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, value: int) -> None:  # pyright: ignore[reportRedeclaration]
        if value != self._currentIndex:
            self._currentIndex = value
            self.currentIndexChanged.emit(value)

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
