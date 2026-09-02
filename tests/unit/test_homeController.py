"""Unit tests for homeController."""

import asyncio
import gc

import pytest
from PySide6.QtCore import QObject

import bingr.controllers.homeController as hcModule
from bingr.common.eventBus import appEventBus
from bingr.common.eventTypes import ReloadChannelsDataEvent
from bingr.controllers.homeController import BOOST_CATEGORIES, HomeController


class FakeHomeListModel(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = None
        self.resetCalls = []

    def resetItems(self, items):
        self.resetCalls.append(items)
        self.items = items


def makeChannelsServiceMock(mocker):
    service = mocker.MagicMock()
    service.getChannelsCount = mocker.AsyncMock(return_value=0)
    service.getRecentlyAddedChannels = mocker.AsyncMock(return_value=[])
    service.getTopCategoryNames = mocker.AsyncMock(return_value=[])
    service.getChannelsByCategory = mocker.AsyncMock(return_value=[])
    return service


def makeWatchSessionServiceMock(mocker):
    service = mocker.MagicMock()
    service.getContinueWatchingChannels = mocker.AsyncMock(return_value=[])
    return service


@pytest.fixture(autouse=True)
def _gcCollect():
    yield
    gc.collect()


async def pumpLoops(n: int = 300) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class TestCheckIfChannelsExistInApp:
    async def testNoChannelsEmitsFalseAndSkipsLoad(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        existSeen = []
        loadingSeen = []
        ctrl = HomeController()
        ctrl.channelsExistInApp.connect(existSeen.append)
        ctrl.loadingChanged.connect(loadingSeen.append)

        await pumpLoops()

        assert existSeen == [False]
        channelsService.getRecentlyAddedChannels.assert_not_called()
        watchService.getContinueWatchingChannels.assert_not_called()
        assert ctrl._loading is False
        # initial value True → only the transition to False is emitted
        assert loadingSeen == [False]

    async def testWithChannelsLoadsAllSections(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=5)
        channelsService.getRecentlyAddedChannels = mocker.AsyncMock(
            return_value=[{"id": 1}, {"id": 2}]
        )
        channelsService.getTopCategoryNames = mocker.AsyncMock(return_value=["News"])
        channelsService.getChannelsByCategory = mocker.AsyncMock(
            return_value=[{"id": 3}]
        )
        watchService = makeWatchSessionServiceMock(mocker)
        watchService.getContinueWatchingChannels = mocker.AsyncMock(
            return_value=[{"id": 4}]
        )
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        existSeen = []
        dataChangedSeen = []
        ctrl = HomeController()
        ctrl.channelsExistInApp.connect(existSeen.append)
        ctrl.homeDataChanged.connect(lambda: dataChangedSeen.append(1))

        await pumpLoops()

        assert existSeen == [True]
        channelsService.getRecentlyAddedChannels.assert_awaited_once_with(limit=30)
        watchService.getContinueWatchingChannels.assert_awaited_once_with(limit=15)
        channelsService.getTopCategoryNames.assert_awaited_once_with(limit=4, boost_names=BOOST_CATEGORIES)
        channelsService.getChannelsByCategory.assert_awaited_once_with(category="News", limit=30)
        assert ctrl._recentlyAddedChannelsModel.items == [{"id": 1}, {"id": 2}]
        assert ctrl._continueWatchingChannelsModel.items == [{"id": 4}]
        assert ctrl._pagerViewModel1SectionTitle == "News"
        assert ctrl._pagerViewModel1.items == [{"id": 3}]
        assert len(dataChangedSeen) == 1
        assert ctrl._loading is False


class TestLoadCategoriesChannels:
    async def _makeCtrl(self, mocker, categories, perCategory):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=3)
        channelsService.getTopCategoryNames = mocker.AsyncMock(return_value=categories)
        channelsService.getChannelsByCategory = mocker.AsyncMock(side_effect=perCategory)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)
        ctrl = HomeController()
        await pumpLoops()
        return ctrl

    async def testFewerThanFourCategoriesLeaveRemainingPagersEmpty(self, mocker):
        ctrl = await self._makeCtrl(
            mocker,
            ["News", "Sports"],
            [[{"id": 1}], [{"id": 2}]],
        )

        assert ctrl._pagerViewModel1SectionTitle == "News"
        assert ctrl._pagerViewModel2SectionTitle == "Sports"
        assert ctrl._pagerViewModel3SectionTitle is None
        assert ctrl._pagerViewModel3 is None
        assert ctrl._pagerViewModel4SectionTitle is None
        assert ctrl._pagerViewModel4 is None

    async def testCategoryWithNoChannelsGetsNonePager(self, mocker):
        ctrl = await self._makeCtrl(mocker, ["News"], [[]])

        assert ctrl._pagerViewModel1SectionTitle is None
        assert ctrl._pagerViewModel1 is None

    async def testMoreThanFourCategoriesOnlyFirstFourUsed(self, mocker):
        categories = ["A", "B", "C", "D", "E", "F"]
        ctrl = await self._makeCtrl(mocker, categories, [[{"id": i}] for i in range(6)])

        assert ctrl._pagerViewModel4SectionTitle == "D"
        titles = [
            ctrl._pagerViewModel1SectionTitle,
            ctrl._pagerViewModel2SectionTitle,
            ctrl._pagerViewModel3SectionTitle,
            ctrl._pagerViewModel4SectionTitle,
        ]
        assert titles == ["A", "B", "C", "D"]


class TestSectionFailures:
    async def testContinueWatchingFailureDoesNotBreakLoad(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=3)
        watchService = makeWatchSessionServiceMock(mocker)
        watchService.getContinueWatchingChannels = mocker.AsyncMock(
            side_effect=RuntimeError("cw boom")
        )
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        dataChangedSeen = []
        ctrl = HomeController()
        ctrl.homeDataChanged.connect(lambda: dataChangedSeen.append(1))

        await pumpLoops()

        assert ctrl._continueWatchingChannelsModel is None
        assert len(dataChangedSeen) == 1

    async def testRecentlyAddedFailureDoesNotBreakOtherSections(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=3)
        channelsService.getRecentlyAddedChannels = mocker.AsyncMock(
            side_effect=RuntimeError("db boom")
        )
        watchService = makeWatchSessionServiceMock(mocker)
        watchService.getContinueWatchingChannels = mocker.AsyncMock(
            return_value=[{"id": 9}]
        )
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        dataChangedSeen = []
        ctrl = HomeController()
        ctrl.homeDataChanged.connect(lambda: dataChangedSeen.append(1))

        await pumpLoops()

        assert ctrl._recentlyAddedChannelsModel is None
        assert ctrl._continueWatchingChannelsModel.items == [{"id": 9}]
        assert len(dataChangedSeen) == 1

    async def testCategoriesFailureStillCompletesLoad(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=3)
        channelsService.getTopCategoryNames = mocker.AsyncMock(
            side_effect=RuntimeError("cat boom")
        )
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        dataChangedSeen = []
        ctrl = HomeController()
        ctrl.homeDataChanged.connect(lambda: dataChangedSeen.append(1))

        await pumpLoops()

        assert all(getattr(ctrl, f"_pagerViewModel{i}") is None for i in range(1, 5))
        assert len(dataChangedSeen) == 1

    async def testEmptyRecentlyAddedLeavesModelNone(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=3)
        channelsService.getRecentlyAddedChannels = mocker.AsyncMock(return_value=[])
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        await pumpLoops()

        assert ctrl._recentlyAddedChannelsModel is None


class TestReloadEvents:
    async def testReloadEventWithDoReloadTriggersFreshCheck(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=0)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        await pumpLoops()
        firstCount = channelsService.getChannelsCount.await_count

        appEventBus.reloadChannelsData.emit(ReloadChannelsDataEvent(doReload=True))
        await pumpLoops()

        assert channelsService.getChannelsCount.await_count == firstCount + 1
        assert ctrl._loading is False

    async def testReloadEventWithoutDoReloadIsIgnored(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=0)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        await pumpLoops()
        countAfterInitial = channelsService.getChannelsCount.await_count

        appEventBus.reloadChannelsData.emit(ReloadChannelsDataEvent(doReload=False))
        await pumpLoops()

        assert channelsService.getChannelsCount.await_count == countAfterInitial
        assert ctrl._loading is False


class TestPlayBridge:
    async def testChannelIdPlayRequestedEmitsSignal(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        seen = []
        ctrl.channelIdToPlay.connect(seen.append)

        ctrl.channelIdPlayRequested(77)

        assert seen == [77]


class TestPropertiesExposeViewModels:
    async def testPropertiesReturnLoadedModelsAndTitles(self, mocker):
        """Exercises all QML-facing Property getters."""
        channelsService = makeChannelsServiceMock(mocker)
        channelsService.getChannelsCount = mocker.AsyncMock(return_value=5)
        channelsService.getRecentlyAddedChannels = mocker.AsyncMock(
            return_value=[{"id": 1}]
        )
        channelsService.getTopCategoryNames = mocker.AsyncMock(
            return_value=["A", "B"]
        )
        channelsService.getChannelsByCategory = mocker.AsyncMock(
            side_effect=[[{"id": 10}], [{"id": 20}]]
        )
        watchService = makeWatchSessionServiceMock(mocker)
        watchService.getContinueWatchingChannels = mocker.AsyncMock(
            return_value=[{"id": 2}]
        )
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        await pumpLoops()

        assert isinstance(ctrl.recentlyAddedChannelsViewModel, FakeHomeListModel)
        assert isinstance(ctrl.continueWatchingChannelsViewModel, FakeHomeListModel)
        assert isinstance(ctrl.pagerViewModel1, FakeHomeListModel)
        assert ctrl.pagerViewModel1SectionTitle == "A"
        assert isinstance(ctrl.pagerViewModel2, FakeHomeListModel)
        assert ctrl.pagerViewModel2SectionTitle == "B"
        assert ctrl.pagerViewModel3 is None
        assert ctrl.pagerViewModel3SectionTitle is None
        assert ctrl.pagerViewModel4 is None
        assert ctrl.pagerViewModel4SectionTitle is None

    async def testLoadingPropertyReflectsState(self, mocker):
        channelsService = makeChannelsServiceMock(mocker)
        watchService = makeWatchSessionServiceMock(mocker)
        mocker.patch.object(hcModule, "ChannelsManagementService", mocker.MagicMock(return_value=channelsService))
        mocker.patch.object(hcModule, "WatchSessionService", mocker.MagicMock(return_value=watchService))
        mocker.patch.object(hcModule, "_HomeChannelsListModel", FakeHomeListModel)

        ctrl = HomeController()
        assert ctrl.loading is True

        await pumpLoops()

        assert ctrl.loading is False
