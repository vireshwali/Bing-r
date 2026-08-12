"""QML bridge for channels screen — loads channel data and exposes ViewModels for Hero, Grid, and List."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement

import bingr.ui_models.categoryFilterViewModel as _catVm
import bingr.ui_models.channelsGridViewModel as _gridVm
import bingr.ui_models.channelsHeroViewModel as _heroVm
import bingr.ui_models.countryFilterViewModel as _countryVm
import bingr.ui_models.homeChannelsListModel as _homeModel
import bingr.ui_models.qualityFilterViewModel as _qualVm
from bingr.common.eventBus import appEventBus
from bingr.common.eventTypes import ReloadChannelsDataEvent
from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.services.watchSessionService import WatchSessionService

_ChannelsHeroViewModel: Any = _heroVm.ChannelsHeroViewModel
_ChannelsGridViewModel: Any = _gridVm.ChannelsGridViewModel
_CategoryFilterViewModel: Any = _catVm.CategoryFilterViewModel
_CountryFilterViewModel: Any = _countryVm.CountryFilterViewModel
_QualityFilterViewModel: Any = _qualVm.QualityFilterViewModel
_HomeChannelsListModel: Any = _homeModel.HomeChannelsListModel

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import ChannelsManagementService as ChannelsManagementServiceType
    from bingr.services.watchSessionService import WatchSessionService as WatchSessionServiceType
else:
    ChannelsManagementServiceType = "ChannelsManagementService"
    WatchSessionServiceType = "WatchSessionService"

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

BOOST_CATEGORIES = ["News", "Entertainment", "Movies", "Music"]


@QmlElement
class HomeController(QObject):
    """Controller for the home screen."""

    loadingChanged = Signal(bool)
    homeDataChanged = Signal()  # dummy signal for binding only.
    channelsExistInApp = Signal(bool)

    # for MainAppScreen to bridge the channelId play reuqested
    channelIdToPlay = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._channelsService: ChannelsManagementServiceType = ChannelsManagementService()
        self._watchSessionService: WatchSessionServiceType = WatchSessionService()
        self._loading = True
        self._recentlyAddedChannelsModel: _HomeChannelsListModel | None = None  # type: ignore
        self._continueWatchingChannelsModel: _HomeChannelsListModel | None = None  # type: ignore

        self._pagerViewModel1SectionTitle: str | None = None
        self._pagerViewModel1: _HomeChannelsListModel | None = None  # type: ignore

        self._pagerViewModel2SectionTitle: str | None = None
        self._pagerViewModel2: _HomeChannelsListModel | None = None  # type: ignore

        self._pagerViewModel3SectionTitle: str | None = None
        self._pagerViewModel3: _HomeChannelsListModel | None = None  # type: ignore

        self._pagerViewModel4SectionTitle: str | None = None
        self._pagerViewModel4: _HomeChannelsListModel | None = None  # type: ignore

        appEventBus.reloadChannelsData.connect(self.onReloadChannelsData)

        asyncio.create_task(self.checkIfChannelsExistInApp())  # noqa: RUF006

    async def checkIfChannelsExistInApp(self):
        try:
            self._setLoading(True)
            count = await self._channelsService.getChannelsCount()
            hasChannels = count > 0
            self.channelsExistInApp.emit(hasChannels)
            if hasChannels:
                await self.loadHomeData()
        finally:
            self._setLoading(False)

    async def loadHomeData(self) -> None:
        """Load data for the home screen sections asynchronously.

        All sections are loaded in parallel; ``loading`` is only switched to
        False once every section has finished. New sections (hero, etc.) get
        appended to this gather.
        """
        await asyncio.gather(
            self.loadRecentlyAddedChannelsViewModel(),
            self.loadContinueWatchingChannelsViewModel(),
            self.loadCategoriesChannels(),
        )
        self.homeDataChanged.emit()

    def _setLoading(self, value: bool) -> None:
        if self._loading == value:
            return
        self._loading = value
        self.loadingChanged.emit(value)

    async def loadContinueWatchingChannelsViewModel(self):
        try:
            channels = await self._watchSessionService.getContinueWatchingChannels(limit=15)
            self._continueWatchingChannelsModel = None
            if channels:
                model = _HomeChannelsListModel(self)
                model.resetItems(channels)
                self._continueWatchingChannelsModel = model
        except Exception as e:
            logger.exception("Failed to load continue watching channels data: %s", e)

    async def loadRecentlyAddedChannelsViewModel(self):
        try:
            # all channels data
            channels = await self._channelsService.getRecentlyAddedChannels(limit=30)
            self._recentlyAddedChannelsModel = None
            if channels:
                model = _HomeChannelsListModel(self)
                model.resetItems(channels)
                self._recentlyAddedChannelsModel = model
        except Exception as e:
            logger.exception("Failed to load recently added channels data: %s", e)

    async def loadCategoriesChannels(self):
        try:
            categoriesList = await self._channelsService.getTopCategoryNames(limit=4, boost_names=BOOST_CATEGORIES)
            if not categoriesList:
                return

            channelsPerCategory = await asyncio.gather(
                *[
                    self._channelsService.getChannelsByCategory(category=category, limit=30)
                    for category in categoriesList
                ]
            )

            # Populate the pager view models for each category section and if less than 4 then set the remaining to None
            for index in range(4):
                if index < len(categoriesList) and index < len(channelsPerCategory) and channelsPerCategory[index]:
                    category = categoriesList[index]
                    model = _HomeChannelsListModel(self)
                    model.resetItems(channelsPerCategory[index])
                    setattr(self, f"_pagerViewModel{index + 1}SectionTitle", category)
                    setattr(self, f"_pagerViewModel{index + 1}", model)
                else:
                    setattr(self, f"_pagerViewModel{index + 1}SectionTitle", None)
                    setattr(self, f"_pagerViewModel{index + 1}", None)
        except Exception as e:
            logger.exception("Failed to load categories channels: %s", e)

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(QObject, notify=loadingChanged)
    def recentlyAddedChannelsViewModel(self) -> QObject:
        return self._recentlyAddedChannelsModel  # type: ignore

    @Property(QObject, notify=loadingChanged)
    def continueWatchingChannelsViewModel(self) -> QObject:
        return self._continueWatchingChannelsModel  # type: ignore

    @Property(QObject, notify=loadingChanged)
    def pagerViewModel1(self) -> QObject:
        return self._pagerViewModel1  # type: ignore

    @Property(str, notify=loadingChanged)
    def pagerViewModel1SectionTitle(self) -> str:
        return self._pagerViewModel1SectionTitle  # type: ignore

    @Property(QObject, notify=loadingChanged)
    def pagerViewModel2(self) -> QObject:
        return self._pagerViewModel2  # type: ignore

    @Property(str, notify=loadingChanged)
    def pagerViewModel2SectionTitle(self) -> str:
        return self._pagerViewModel2SectionTitle  # type: ignore

    @Property(QObject, notify=loadingChanged)
    def pagerViewModel3(self) -> QObject:
        return self._pagerViewModel3  # type: ignore

    @Property(str, notify=loadingChanged)
    def pagerViewModel3SectionTitle(self) -> str:
        return self._pagerViewModel3SectionTitle  # type: ignore

    @Property(QObject, notify=loadingChanged)
    def pagerViewModel4(self) -> QObject:
        return self._pagerViewModel4  # type: ignore

    @Property(str, notify=loadingChanged)
    def pagerViewModel4SectionTitle(self) -> str:
        return self._pagerViewModel4SectionTitle  # type: ignore

    @Slot(object)
    def onReloadChannelsData(self, event: ReloadChannelsDataEvent) -> None:
        if event.doReload:
            logger.info("Reloading channels data event received...")
            asyncio.create_task(self.checkIfChannelsExistInApp())  # noqa: RUF006

    @Slot(int)
    def channelIdPlayRequested(self, channelId: int) -> None:
        """Intermediate slot to catch the channel id from a home pager card play button click and
        pass it to the channelIdToPlay signal which is handled in the main MainAppScreen connection.

        Args:
            channelId (int): Primary key of the channel to play.
        """
        self.channelIdToPlay.emit(channelId)
        logger.info("home channelIdToPlay is %s", channelId)
