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

from bingr.ui_models.subtitleModel import SubtitleModel

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1

_INVALID_INDEX = QModelIndex()

logger = logging.getLogger(__name__)


@QmlElement  # type: ignore[reportGeneralTypeIssues]
class SubtitlesViewModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    TrackIdRole = Qt.ItemDataRole.UserRole + 2
    LangCodeRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[SubtitleModel] = []

    def resetItems(self, items: list[SubtitleModel]) -> None:
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

    def _getItemValue(self, item: SubtitleModel, role: int) -> object | None:
        roleMap = {
            self.NameRole: "name",
            self.TrackIdRole: "trackId",
            self.LangCodeRole: "langCode",
        }
        attr = roleMap.get(role)
        return getattr(item, attr, None) if attr else None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"name"),
            self.TrackIdRole: QByteArray(b"trackId"),
            self.LangCodeRole: QByteArray(b"langCode"),
        }
