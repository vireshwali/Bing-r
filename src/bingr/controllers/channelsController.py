"""QML bridge for channels screen — loads channel data and exposes ViewModels for Hero, Grid, and List."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlSingleton

import bingr.ui_models.categoryFilterViewModel as _catVm
import bingr.ui_models.channelsGridViewModel as _gridVm
import bingr.ui_models.channelsHeroViewModel as _heroVm
import bingr.ui_models.countryFilterViewModel as _countryVm
import bingr.ui_models.qualityFilterViewModel as _qualVm
from bingr.common.eventBus import appEventBus
from bingr.services.channelsManagementService import ChannelsManagementService

_ChannelsHeroViewModel: Any = _heroVm.ChannelsHeroViewModel
_ChannelsGridViewModel: Any = _gridVm.ChannelsGridViewModel
_CategoryFilterViewModel: Any = _catVm.CategoryFilterViewModel
_CountryFilterViewModel: Any = _countryVm.CountryFilterViewModel
_QualityFilterViewModel: Any = _qualVm.QualityFilterViewModel

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import ChannelsManagementService as ChannelsManagementServiceType
else:
    ChannelsManagementServiceType = "ChannelsManagementService"

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlSingleton
class ChannelsController(QObject):
    """Controller for the channels screen.

    Exposes UI state (loading, totalCount, error) and two ViewModels:
    - channelsHeroViewModel: top channels for the hero carousel (by visit count)
    - channelsViewModel: paginated channel list for Grid and List views
    """

    errorChanged = Signal(str)
    gridIsLoading = Signal(bool)
    heroSectionIsLoading = Signal(bool)

    # for MainAppScreen to bridge the channelId play reuqested
    channelIdToPlay = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._heroViewModel: Any = _ChannelsHeroViewModel(self)
        self._channelsGridViewModel: Any = _ChannelsGridViewModel(self)
        self._categoryFilterVM: Any = _CategoryFilterViewModel(self)
        self._countryFilterVM: Any = _CountryFilterViewModel(self)
        self._qualityFilterVM: Any = _QualityFilterViewModel(self)
        self._service: ChannelsManagementServiceType = ChannelsManagementService()

        self._loading: bool = False
        self._totalCount: int = 0
        self._error: str = ""
        self._searchText: str = ""

        self._heroViewModel.setService(self._service)
        self._channelsGridViewModel.setService(self._service)
        for vm in [self._categoryFilterVM, self._countryFilterVM, self._qualityFilterVM]:
            vm.setService(self._service)

        self._heroViewModel.isLoading.connect(self.heroSectionIsLoading)
        self._channelsGridViewModel.isLoading.connect(self.gridIsLoading)

        appEventBus.favoriteToggled.connect(self._onFavoriteToggled)

        self._loadChannels()

    @Property(QObject, constant=True)
    def channelsHeroViewModel(self) -> QObject:
        return self._heroViewModel

    @Property(QObject, constant=True)
    def channelsViewModel(self) -> QObject:
        return self._channelsGridViewModel

    @Property(QObject, constant=True)
    def categoryFilterModel(self) -> QObject:
        return self._categoryFilterVM

    @Property(QObject, constant=True)
    def countryFilterModel(self) -> QObject:
        return self._countryFilterVM

    @Property(QObject, constant=True)
    def qualityFilterModel(self) -> QObject:
        return self._qualityFilterVM

    def _getError(self) -> str:
        return self._error

    def _setError(self, value: str) -> None:
        if self._error != value:
            self._error = value
            self.errorChanged.emit(value)

    error: Property = Property(str, _getError, _setError, notify=errorChanged)

    def _loadChannels(self) -> None:
        """Trigger hero and grid channel loads."""
        self._channelsGridViewModel.setFilters()

    @Slot(int)
    def channelIdPlayRequested(self, channelId: int):
        """Intermediate slot to catch the channel id from play button click on channels grid card and pass
        it to the channelIdToPlay signal which is handled in the main MainAppScreen connection.

        Args:
            channelId (int): _description_
        """
        # self._channelId = channelId
        self.channelIdToPlay.emit(channelId)
        logger.info("channelIdPTolay is %s ", channelId)

    @Slot(int)
    def toggleFavorite(self, channelId: int) -> None:
        """Fire-and-forget: emit the toggle request on the event bus.

        FavoritesController persists the change and emits favoriteToggled,
        which updates the grid row in place (no pagination reset).
        """
        appEventBus.toggleFavoriteRequested.emit(channelId)
        logger.info("Favorite toggle requested for channel %s", channelId)

    @Slot(int, bool)
    def _onFavoriteToggled(self, channelId: int, isFavorite: bool) -> None:
        row = self._channelsGridViewModel.findChannelRow(channelId)
        if row >= 0:
            self._channelsGridViewModel.updateItem(row, isFavorite=isFavorite)

    @Slot()
    def applyFilters(self) -> None:
        filters: dict[str, str] = {}
        cat = self._categoryFilterVM.currentValue
        cty = self._countryFilterVM.currentValue
        qual = self._qualityFilterVM.currentValue
        if cat != "all":
            filters["category"] = cat
        if cty != "all":
            filters["country"] = cty
        if qual != "all":
            filters["quality"] = qual
        if self._searchText:
            filters["search"] = self._searchText

        logger.info("filters selected are: %s", filters)
        self._channelsGridViewModel.setFilters(**filters)

    @Slot(str)
    def applyFiltersWithSearch(self, searchText: str) -> None:
        self._searchText = searchText
        filters: dict[str, str] = {}
        cat = self._categoryFilterVM.currentValue
        cty = self._countryFilterVM.currentValue
        qual = self._qualityFilterVM.currentValue
        if cat != "all":
            filters["category"] = cat
        if cty != "all":
            filters["country"] = cty
        if qual != "all":
            filters["quality"] = qual
        if self._searchText:
            filters["search"] = self._searchText

        logger.info("filters selected are: %s", filters)
        self._channelsGridViewModel.setFilters(**filters)
