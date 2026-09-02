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

from bingr.ui_models.channelDataModel import ChannelDataModel

_INV_INDEX = QModelIndex()

QML_IMPORT_NAME = "bingr.models"
QML_IMPORT_MAJOR_VERSION = 1


logger = logging.getLogger(__name__)


@QmlElement
class HomeChannelsListModel(QAbstractListModel):
    """Read-only QAbstractListModel for home screen pager sections.

    Exposes the role names expected by the ``PagerCard`` delegate and is
    populated wholesale via :meth:`resetItems`. Used only as a property value on
    a controller, hence not registered as a QML element.
    """

    ChannelIdRole = Qt.ItemDataRole.UserRole + 1
    DisplayNameRole = Qt.ItemDataRole.UserRole + 2
    LogoUrlRole = Qt.ItemDataRole.UserRole + 3
    CountryCodeRole = Qt.ItemDataRole.UserRole + 4
    CategoryRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[ChannelDataModel] = []

    def resetItems(self, items: list[ChannelDataModel]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _INV_INDEX) -> int:
        return len(self._items)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        roleMap = {
            self.ChannelIdRole: item.channelId,
            self.DisplayNameRole: item.displayName,
            self.LogoUrlRole: item.logoUrl,
            self.CountryCodeRole: item.countryCode,
            self.CategoryRole: item.category,
        }
        return roleMap.get(role)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ChannelIdRole: QByteArray(b"channelId"),
            self.DisplayNameRole: QByteArray(b"displayName"),
            self.LogoUrlRole: QByteArray(b"logoUrl"),
            self.CountryCodeRole: QByteArray(b"countryCode"),
            self.CategoryRole: QByteArray(b"category"),
        }
