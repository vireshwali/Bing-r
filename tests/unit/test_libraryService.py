"""Unit tests for LibraryService — query construction with a mocked session.

``DatabaseManager.get_sessionmaker`` is patched to return a fake async
sessionmaker whose context manager yields a mocked session; ``execute`` returns
a mocked result whose scalar/scalars accessors are configured per test. These
tests cover the query-shaping logic (filters, ordering, limit) without a DB.
"""

from types import SimpleNamespace

import pytest

from bingr.db.dbManager import DatabaseManager
from bingr.services.libraryService import LibraryService


class LibraryTestBase:
    @pytest.fixture
    def session(self, mocker):
        result = mocker.MagicMock()
        session = mocker.MagicMock()
        session.execute = mocker.AsyncMock(return_value=result)
        return session, result

    @pytest.fixture
    def service(self, mocker, session):
        smock, _result = session
        sm = mocker.MagicMock()
        sm.return_value.__aenter__ = mocker.AsyncMock(return_value=smock)
        sm.return_value.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=sm)
        return LibraryService()


class TestGetChannel(LibraryTestBase):
    async def testReturnsChannelById(self, service, session):
        smock, result = session
        channel = SimpleNamespace(channel_id="abc.xyz", display_name="ABC")
        result.scalar_one_or_none.return_value = channel

        found = await service.getChannel("abc.xyz")

        assert found is channel
        stmt = smock.execute.call_args.args[0]
        compiled = str(stmt)
        assert "channels" in compiled
        assert "channel_id" in compiled

    async def testReturnsNoneWhenMissing(self, service, session):
        _smock, result = session
        result.scalar_one_or_none.return_value = None

        assert await service.getChannel("nope") is None


class TestListSources(LibraryTestBase):
    async def testReturnsAllSourcesOrdered(self, service, session):
        smock, result = session
        sources = [SimpleNamespace(id=1, name="A"), SimpleNamespace(id=2, name="B")]
        result.scalars.return_value.all.return_value = sources

        got = await service.listSources()

        assert got == sources
        stmt = smock.execute.call_args.args[0]
        assert "m3u_sources" in str(stmt)

    async def testEmptyResult(self, service, session):
        _smock, result = session
        result.scalars.return_value.all.return_value = []

        assert await service.listSources() == []


class TestListChannels(LibraryTestBase):
    async def testAllChannelsOrderedByDisplayName(self, service, session):
        smock, result = session
        channels = [SimpleNamespace(display_name="A"), SimpleNamespace(display_name="B")]
        result.scalars.return_value.all.return_value = channels

        got = await service.listChannels()

        assert got == channels
        stmt = smock.execute.call_args.args[0]
        compiled = str(stmt)
        assert "display_name" in compiled
        assert "m3u_channels" not in compiled  # unfiltered query has no join

    async def testFilteredBySourceJoinsLinks(self, service, session):
        smock, result = session
        result.scalars.return_value.all.return_value = []

        got = await service.listChannels(source_id=3)

        assert got == []
        stmt = smock.execute.call_args.args[0]
        compiled = str(stmt)
        assert "m3u_channels" in compiled  # join on the many-to-many link
        assert "EXISTS" in compiled  # m3u_links.has(source_id=...)


class TestSearchChannels(LibraryTestBase):
    async def testIlikePatternAndLimit(self, service, session):
        smock, result = session
        channels = [SimpleNamespace(display_name="BHT 1")]
        result.scalars.return_value.all.return_value = channels

        got = await service.searchChannels("bht")

        assert got == channels
        stmt = smock.execute.call_args.args[0]
        assert stmt._limit == 50
        assert "like" in str(stmt).lower()

    async def testEmptyResults(self, service, session):
        _smock, result = session
        result.scalars.return_value.all.return_value = []

        assert await service.searchChannels("zzz-nonexistent") == []
