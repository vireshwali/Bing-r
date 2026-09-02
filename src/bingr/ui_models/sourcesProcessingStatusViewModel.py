from __future__ import annotations

import logging

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, QPersistentModelIndex, Qt

from bingr.ui_models.sourcesProcessingStatusModel import SourcesProcessingStatusModel

_INVALID_INDEX = QModelIndex()

logger = logging.getLogger(__name__)


class SourcesProcessingStatusViewModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    StatusRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[SourcesProcessingStatusModel] = []

    def resetItems(self, items: list[SourcesProcessingStatusModel]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def updateItem(self, row: int, status: str) -> None:
        if 0 <= row < len(self._items):
            self._items[row].status = status
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.StatusRole])

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INVALID_INDEX) -> int:
        return len(self._items)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == self.NameRole:
            return item.name
        if role == self.StatusRole:
            return item.status
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"name"),
            self.StatusRole: QByteArray(b"status"),
        }
