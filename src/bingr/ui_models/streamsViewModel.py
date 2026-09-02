from __future__ import annotations

import logging

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtQml import QmlElement

from bingr.ui_models.streamModel import StreamModel

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1

_INVALID_INDEX = QModelIndex()

logger = logging.getLogger(__name__)


@QmlElement  # type: ignore[reportGeneralTypeIssues]
class StreamsViewModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    UrlRole = Qt.ItemDataRole.UserRole + 2
    LangCodeRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[StreamModel] = []

    def resetItems(self, items: list[StreamModel]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INVALID_INDEX) -> int:
        return len(self._items)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        return self._getItemValue(item, role)

    def _getItemValue(self, item: StreamModel, role: int) -> object | None:
        roleMap = {
            self.NameRole: "name",
            self.UrlRole: "url",
            self.LangCodeRole: "langCode",
        }
        attr = roleMap.get(role)
        return getattr(item, attr, None) if attr else None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"name"),
            self.UrlRole: QByteArray(b"url"),
            self.LangCodeRole: QByteArray(b"langCode"),
        }
