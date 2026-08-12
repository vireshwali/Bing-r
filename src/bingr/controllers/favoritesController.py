"""QML bridge for favourites — toggle persistence and favourites grid viewmodel."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement

import bingr.ui_models.channelsGridViewModel as _gridVm
from bingr.common.eventBus import appEventBus
from bingr.services.channelsManagementService import ChannelsManagementService

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import ChannelsManagementService as ChannelsManagementServiceType

_ChannelsGridViewModel: Any = _gridVm.ChannelsGridViewModel

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
class FavoritesController(QObject):
    """Handles favorite toggles and exposes the favourites grid viewmodel.

    Listens on the event bus: ``toggleFavoriteRequested`` persists the change
    and emits ``favoriteToggled``. The favourites grid is reloaded whenever
    a channel's favourite state changes.
    """

    gridIsLoading = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service: ChannelsManagementServiceType = ChannelsManagementService()

        self._gridViewModel: Any = _ChannelsGridViewModel(self)
        self._gridViewModel.setService(self._service)
        self._gridViewModel.isLoading.connect(self.gridIsLoading)
        self._gridViewModel.setFilters(favorite="true")

        appEventBus.toggleFavoriteRequested.connect(self._onToggleRequested)
        appEventBus.favoriteToggled.connect(self._onFavoriteToggled)

    @Property(QObject, constant=True)
    def favoritesGridViewModel(self) -> QObject:
        return self._gridViewModel

    @Slot(int)
    def _onToggleRequested(self, channelId: int) -> None:
        asyncio.ensure_future(self._doToggle(channelId))  # noqa: RUF006

    async def _doToggle(self, channelId: int) -> None:
        isFavorite = await self._service.toggleFavorite(channelId)
        appEventBus.favoriteToggled.emit(channelId, isFavorite)
        logger.info("Channel %s favorite state is now: %s", channelId, isFavorite)

    @Slot(int, bool)
    def _onFavoriteToggled(self, channelId: int, isFavorite: bool) -> None:
        """Reload the favourites grid on any favourite change.

        Covers: favourite from Channels UI, unfavourite from Channels UI,
        and unfavourite from the Favourites UI itself.
        """
        self._gridViewModel.setFilters(favorite="true")
        logger.info("Reloaded favourites grid after toggle of channel %s", channelId)
