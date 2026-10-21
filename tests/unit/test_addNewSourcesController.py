"""Unit tests for addNewSourcesController — processingActive lifecycle and task completion."""

import asyncio

import pytest

import bingr.controllers.addNewSourcesController as anscModule
from bingr.common.eventBus import appEventBus
from bingr.controllers.addNewSourcesController import AddNewSourcesController
from bingr.ui_models.sourcesProcessingStatusViewModel import SourcesProcessingStatusViewModel


async def pumpLoops(n: int = 400) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def _auditLogMock(mocker):
    return mocker.patch.object(anscModule, "auditLog", mocker.AsyncMock(return_value=None))


def makeImportMock(mocker, sideEffect):
    return mocker.patch.object(anscModule.importerService, "importM3u", side_effect=sideEffect)


class TestProcessingActiveProperty:
    async def testInitiallyInactive(self):
        ctrl = AddNewSourcesController()
        assert ctrl.processingActive is False

    async def testActiveDuringImportAndInactiveAfterCompletion(self, mocker):
        release = asyncio.Event()

        async def fakeImport(**_kwargs):
            await release.wait()
            return mocker.Mock(id=1, channel_count=2)

        makeImportMock(mocker, fakeImport)
        seen = []
        ctrl = AddNewSourcesController()
        ctrl.processingActiveChanged.connect(seen.append)

        ctrl.processM3UFiles(["http://example.com/pl.m3u"])
        await pumpLoops()
        assert ctrl.processingActive is True

        release.set()
        await pumpLoops()
        assert ctrl.processingActive is False
        assert seen == [True, False]

    async def testConcurrentImportsStayActiveUntilAllFinish(self, mocker):
        releaseFirst = asyncio.Event()
        releaseSecond = asyncio.Event()
        callCount = 0

        async def fakeImport(**_kwargs):
            nonlocal callCount
            callCount += 1
            if callCount == 1:
                await releaseFirst.wait()
            else:
                await releaseSecond.wait()
            return mocker.Mock(id=callCount, channel_count=1)

        makeImportMock(mocker, fakeImport)
        ctrl = AddNewSourcesController()

        ctrl.processM3UFiles(["http://example.com/a.m3u"])
        await pumpLoops()
        ctrl.processM3UFiles(["http://example.com/b.m3u"])
        await pumpLoops()
        assert ctrl.processingActive is True

        releaseFirst.set()
        await pumpLoops()
        assert ctrl.processingActive is True

        releaseSecond.set()
        await pumpLoops()
        assert ctrl.processingActive is False


class TestTaskCompletion:
    async def testReloadChannelsDataEventFiresOnCompletion(self, mocker):
        async def fakeImport(**_kwargs):
            return mocker.Mock(id=1, channel_count=0)

        makeImportMock(mocker, fakeImport)
        events = []

        def handler(event):
            events.append(event)

        appEventBus.reloadChannelsData.connect(handler)
        try:
            ctrl = AddNewSourcesController()
            ctrl.processM3UFiles(["http://example.com/pl.m3u"])
            await pumpLoops()
            assert len(events) == 1
        finally:
            appEventBus.reloadChannelsData.disconnect(handler)

    async def testDoneCallbackLogsTaskExceptionAndStillFiresReload(self, mocker):
        mocker.patch.object(
            SourcesProcessingStatusViewModel,
            "resetItems",
            side_effect=RuntimeError("vm boom"),
        )
        logException = mocker.patch.object(anscModule.logger, "exception")
        events = []

        def handler(event):
            events.append(event)

        appEventBus.reloadChannelsData.connect(handler)
        try:
            ctrl = AddNewSourcesController()
            ctrl.processM3UFiles(["http://example.com/pl.m3u"])
            await pumpLoops()
            assert ctrl.processingActive is False
            assert logException.called
            assert len(events) == 1
        finally:
            appEventBus.reloadChannelsData.disconnect(handler)
