"""Unit tests for channelsController."""

import asyncio
import gc

import pytest
from PySide6.QtCore import QObject, Signal

import bingr.controllers.channelsController as ccModule
from bingr.common.eventBus import appEventBus
from bingr.controllers.channelsController import ChannelsController


class FakeLoadingVm(QObject):
    isLoading = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = None

    def setService(self, service):
        self.service = service


class FakeGridVM(FakeLoadingVm):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filtersHistory = []
        self.rowForChannel = -1
        self.updateItemCalls = []

    def setFilters(self, **filters):
        self.filtersHistory.append(filters)

    def findChannelRow(self, channelId):
        return self.rowForChannel

    def updateItem(self, row, **fields):
        self.updateItemCalls.append((row, fields))


class FakeFilterVM(FakeLoadingVm):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentValue = "all"


@pytest.fixture(autouse=True)
def _patchModule(mocker, monkeypatch):
    service = mocker.MagicMock()
    monkeypatch.setattr(ccModule, "ChannelsManagementService", mocker.MagicMock(return_value=service))
    monkeypatch.setattr(ccModule, "_ChannelsHeroViewModel", FakeLoadingVm)
    monkeypatch.setattr(ccModule, "_ChannelsGridViewModel", FakeGridVM)
    monkeypatch.setattr(ccModule, "_CategoryFilterViewModel", FakeFilterVM)
    monkeypatch.setattr(ccModule, "_CountryFilterViewModel", FakeFilterVM)
    monkeypatch.setattr(ccModule, "_QualityFilterViewModel", FakeFilterVM)
    _patchModule.service = service
    yield


@pytest.fixture(autouse=True)
def _gcCollect():
    yield
    gc.collect()


def makeController():
    return ChannelsController()


async def pumpLoops(n: int = 200) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class TestInit:
    def testServiceInjectedIntoAllViewModels(self):
        ctrl = makeController()
        service = _patchModule.service

        assert ctrl._heroViewModel.service is service
        assert ctrl._channelsGridViewModel.service is service
        assert ctrl._categoryFilterVM.service is service
        assert ctrl._countryFilterVM.service is service
        assert ctrl._qualityFilterVM.service is service

    def testConstructorTriggersInitialLoad(self):
        ctrl = makeController()

        assert ctrl._channelsGridViewModel.filtersHistory == [{}]

    def testPropertiesExposeViewModels(self):
        ctrl = makeController()

        assert ctrl.channelsHeroViewModel is ctrl._heroViewModel
        assert ctrl.channelsViewModel is ctrl._channelsGridViewModel
        assert ctrl.categoryFilterModel is ctrl._categoryFilterVM
        assert ctrl.countryFilterModel is ctrl._countryFilterVM
        assert ctrl.qualityFilterModel is ctrl._qualityFilterVM

    async def testViewModelLoadingSignalsAreForwarded(self):
        ctrl = makeController()
        heroEmissions = []
        gridEmissions = []
        ctrl.heroSectionIsLoading.connect(heroEmissions.append)
        ctrl.gridIsLoading.connect(gridEmissions.append)

        ctrl._heroViewModel.isLoading.emit(True)
        ctrl._channelsGridViewModel.isLoading.emit(False)

        assert heroEmissions == [True]
        assert gridEmissions == [False]


class TestPlayBridge:
    def testChannelIdPlayRequestedEmitsSignal(self):
        ctrl = makeController()
        seen = []
        ctrl.channelIdToPlay.connect(seen.append)

        ctrl.channelIdPlayRequested(99)

        assert seen == [99]


class TestFavoriteBridge:
    async def testToggleFavoriteCallsServiceAndEmitsToggled(self, mocker):
        ctrl = makeController()
        ctrl._service.toggleFavorite = mocker.AsyncMock(return_value=True)
        seen = []
        appEventBus.favoriteToggled.connect(lambda cid, fav: seen.append((cid, fav)))

        ctrl.toggleFavorite(5)
        await pumpLoops()

        ctrl._service.toggleFavorite.assert_awaited_once_with(5)
        assert seen == [(5, True)]

    def testOnFavoriteToggledUpdatesGridRow(self):
        ctrl = makeController()
        ctrl._channelsGridViewModel.rowForChannel = 4

        ctrl._onFavoriteToggled(12, True)

        assert ctrl._channelsGridViewModel.updateItemCalls == [(4, {"isFavorite": True})]

    def testOnFavoriteToggledIgnoresMissingRow(self):
        ctrl = makeController()
        ctrl._channelsGridViewModel.rowForChannel = -1

        ctrl._onFavoriteToggled(12, True)

        assert ctrl._channelsGridViewModel.updateItemCalls == []


class TestFilters:
    def testApplyFiltersWithAllDefaultsSendsNoFilters(self):
        ctrl = makeController()
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFilters()

        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [{}]

    def testApplyFiltersIncludesOnlyNonDefaultSelections(self):
        ctrl = makeController()
        ctrl._categoryFilterVM.currentValue = "News"
        ctrl._qualityFilterVM.currentValue = "hd"
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFilters()

        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [{"category": "News", "quality": "hd"}]

    def testApplyFiltersWithSearchAddsSearchTerm(self):
        ctrl = makeController()
        ctrl._countryFilterVM.currentValue = "IN"
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFiltersWithSearch("sports")

        assert ctrl._searchText == "sports"
        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [{"country": "IN", "search": "sports"}]

    def testApplyFiltersWithSearchIncludesCategoryAndQuality(self):
        ctrl = makeController()
        ctrl._categoryFilterVM.currentValue = "Movies"
        ctrl._qualityFilterVM.currentValue = "sd"
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFiltersWithSearch("war")

        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [
            {"category": "Movies", "quality": "sd", "search": "war"}
        ]

    def testApplyFiltersWithSearchPersistsForLaterApplies(self):
        ctrl = makeController()
        ctrl.applyFiltersWithSearch("news")
        ctrl._categoryFilterVM.currentValue = "Movies"
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFilters()

        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [{"category": "Movies", "search": "news"}]

    def testApplyFiltersCountryOnlySelection(self):
        ctrl = makeController()
        ctrl._countryFilterVM.currentValue = "US"
        initialLoads = len(ctrl._channelsGridViewModel.filtersHistory)

        ctrl.applyFilters()

        assert ctrl._channelsGridViewModel.filtersHistory[initialLoads:] == [{"country": "US"}]


class TestErrorProperty:
    def testSetErrorEmitsChangedSignal(self):
        ctrl = makeController()
        seen = []
        ctrl.errorChanged.connect(seen.append)

        ctrl.error = "boom"

        assert seen == ["boom"]
        assert ctrl.error == "boom"

    def testSetSameErrorDoesNotReemit(self):
        ctrl = makeController()
        ctrl.error = "boom"
        seen = []
        ctrl.errorChanged.connect(seen.append)

        ctrl.error = "boom"

        assert seen == []
