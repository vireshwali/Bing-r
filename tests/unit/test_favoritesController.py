"""Unit tests for favoritesController."""

import asyncio
import gc

import pytest
from PySide6.QtCore import QObject, Signal

import bingr.controllers.favoritesController as fcModule
from bingr.common.eventBus import appEventBus
from bingr.controllers.favoritesController import FavoritesController


class FakeGridVM(QObject):
    isLoading = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = None
        self.filtersHistory = []

    def setService(self, service):
        self.service = service

    def setFilters(self, **filters):
        self.filtersHistory.append(filters)


@pytest.fixture(autouse=True)
def _patchModule(mocker, monkeypatch):
    service = mocker.MagicMock()
    service.toggleFavorite = mocker.AsyncMock(return_value=True)
    monkeypatch.setattr(fcModule, "ChannelsManagementService", mocker.MagicMock(return_value=service))
    monkeypatch.setattr(fcModule, "_ChannelsGridViewModel", FakeGridVM)
    _patchModule.service = service
    yield


@pytest.fixture(autouse=True)
def _gcCollect():
    """Drop bus connections held by controllers from finished tests."""
    yield
    gc.collect()


def makeController():
    return FavoritesController()


async def pumpLoops(n: int = 200) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class TestInit:
    async def testGridConfiguredWithFavoriteFilter(self):
        ctrl = makeController()

        assert ctrl._gridViewModel.service is fcModule.ChannelsManagementService.return_value
        assert ctrl._gridViewModel.filtersHistory == [{"favorite": "true"}]

    def testFavoritesGridViewModelPropertyReturnsVm(self):
        ctrl = makeController()

        assert ctrl.favoritesGridViewModel is ctrl._gridViewModel


class TestToggleFlow:
    async def testDoTogglePersistsAndEmitsBusEvent(self, mocker):
        service = _patchModule.service
        ctrl = makeController()
        seen = []
        appEventBus.favoriteToggled.connect(lambda cid, fav: seen.append((cid, fav)))

        await ctrl._doToggle(7)

        service.toggleFavorite.assert_awaited_once_with(7)
        assert seen == [(7, True)]

    async def testOnToggleRequestedSchedulesAsyncToggle(self, mocker):
        """The slot is fire-and-forget; pump the loop until the toggle lands."""
        service = _patchModule.service
        ctrl = makeController()
        mocker.patch.object(ctrl, "_doToggle", wraps=ctrl._doToggle)

        ctrl._onToggleRequested(3)
        await pumpLoops(100)

        ctrl._doToggle.assert_awaited_once_with(3)
        service.toggleFavorite.assert_awaited_once_with(3)

    async def testOnFavoriteToggledReloadsFavouritesGrid(self, mocker):
        ctrl = makeController()
        initialLoads = len(ctrl._gridViewModel.filtersHistory)

        ctrl._onFavoriteToggled(42, False)

        assert len(ctrl._gridViewModel.filtersHistory) == initialLoads + 1
        assert ctrl._gridViewModel.filtersHistory[-1] == {"favorite": "true"}

    async def testToggleFromBusEndToEnd(self, mocker):
        """toggleFavoriteRequested → persist → favoriteToggled → grid reload."""
        service = _patchModule.service
        ctrl = makeController()
        loadsBefore = len(ctrl._gridViewModel.filtersHistory)

        appEventBus.toggleFavoriteRequested.emit(11)
        await pumpLoops()

        service.toggleFavorite.assert_awaited_once_with(11)
        # one reload comes from the controller's own favoriteToggled handler
        assert len(ctrl._gridViewModel.filtersHistory) == loadsBefore + 1
