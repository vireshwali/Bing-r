"""Unit tests for WatchSessionService — persistence and history queries.

``DatabaseManager.get_sessionmaker`` is patched to yield a mocked async session
and ``ChannelsManagementService`` is replaced with a mock, so these tests cover
the session-row construction and the aggregate query/mapping logic without a DB.
"""

from types import SimpleNamespace

import pytest

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import WatchSession
from bingr.services import watchSessionService as watch_module
from bingr.services.watchSessionService import WatchSessionService


class WatchSessionTestBase:
    @pytest.fixture
    def session(self, mocker):
        result = mocker.MagicMock()
        session = mocker.MagicMock()
        session.execute = mocker.AsyncMock(return_value=result)
        session.commit = mocker.AsyncMock()
        session.refresh = mocker.AsyncMock()
        return session, result

    @pytest.fixture
    def channelsService(self, mocker):
        return mocker.patch.object(watch_module, "ChannelsManagementService")

    @pytest.fixture
    def service(self, mocker, session, channelsService):
        smock, _result = session
        sm = mocker.MagicMock()
        sm.return_value.__aenter__ = mocker.AsyncMock(return_value=smock)
        sm.return_value.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=sm)
        return WatchSessionService()


class TestRecordSession(WatchSessionTestBase):
    async def testPersistsSessionRow(self, service, session):
        smock, _result = session

        ws = await service.recordSession(
            channelPk=7,
            startedAt="2026-08-05T10:00:00",
            endedAt="2026-08-05T10:30:00",
            durationSeconds=1800,
            completed=True,
        )

        assert isinstance(ws, WatchSession)
        assert ws.channel_id == 7
        assert ws.started_at == "2026-08-05T10:00:00"
        assert ws.ended_at == "2026-08-05T10:30:00"
        assert ws.duration_seconds == 1800
        assert ws.completed is True
        smock.add.assert_called_once_with(ws)
        smock.commit.assert_awaited_once()
        smock.refresh.assert_awaited_once_with(ws)

    async def testDefaultsCompletedFalse(self, service, session):
        smock, _result = session

        ws = await service.recordSession(1, "2026-08-05T10:00:00", "2026-08-05T10:10:00", 600)

        assert ws.completed is False
        assert ws.channel_id == 1
        smock.commit.assert_awaited_once()


class TestGetContinueWatchingChannels(WatchSessionTestBase):
    async def testMapsChannelsViaChannelsService(self, service, session, channelsService):
        smock, result = session
        ch1 = SimpleNamespace(id=1, display_name="One")
        ch2 = SimpleNamespace(id=2, display_name="Two")
        result.scalars.return_value.unique.return_value.all.return_value = [ch1, ch2]
        channelsService.return_value.mapChannel.side_effect = lambda c: f"mapped:{c.display_name}"

        got = await service.getContinueWatchingChannels(limit=5)

        assert got == ["mapped:One", "mapped:Two"]
        stmt = smock.execute.call_args.args[0]
        assert stmt._limit == 5
        assert "GROUP BY" in str(stmt)

    async def testEmptyHistoryReturnsEmpty(self, service, session):
        _smock, result = session
        result.scalars.return_value.unique.return_value.all.return_value = []

        assert await service.getContinueWatchingChannels() == []


class TestGetTopChannelsByWatchTime(WatchSessionTestBase):
    async def testReturnsChannelDurationPairs(self, service, session):
        smock, result = session
        ch1 = SimpleNamespace(id=1, display_name="One")
        result.all.return_value = [(ch1, 3000)]

        got = await service.getTopChannelsByWatchTime(limit=10)

        assert got == [(ch1, 3000)]
        stmt = smock.execute.call_args.args[0]
        assert stmt._limit == 10
        assert "GROUP BY" in str(stmt)

    async def testEmptyHistoryReturnsEmpty(self, service, session):
        _smock, result = session
        result.all.return_value = []

        assert await service.getTopChannelsByWatchTime() == []


class TestCountSessions(WatchSessionTestBase):
    async def testReturnsCount(self, service, session):
        _smock, result = session
        result.scalar_one.return_value = 42

        assert await service.countSessions() == 42
