"""Integration tests for ChannelsManagementService against the real DB.

Seeds a dedicated source (\"cms_test\") via importM3u, then exercises
all public query/mutation methods.
"""

import shutil
import uuid

import pytest

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, Feed
from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.services.importerService import importM3u

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seededSource(dbSessionmaker, sample_m3u, tmp_path):
    localCopy = tmp_path / "sample.m3u"
    shutil.copy(sample_m3u, localCopy)
    # Unique source name per test to avoid conflicts
    sourceName = f"cms_test_{uuid.uuid4().hex[:8]}"
    source = await importM3u(sourceName=sourceName, m3uPath=localCopy)

    yield source

    # Cleanup: delete this source's channels and links
    sm = DatabaseManager.get_sessionmaker()
    async with sm() as session:
        from sqlalchemy import delete, select

        from bingr.db.models import Channel, Feed, M3UChannel, M3USource
        src = (await session.execute(select(M3USource).where(M3USource.name == sourceName))).scalar_one_or_none()
        if src:
            chIds = (await session.execute(select(Channel.id).where(Channel.m3u_links.any(M3UChannel.source_id == src.id)))).scalars().all()
            if chIds:
                await session.execute(delete(Feed).where(Feed.channel_id.in_(chIds)))
                await session.execute(delete(M3UChannel).where(M3UChannel.channel_id.in_(chIds)))
                await session.execute(delete(Channel).where(Channel.id.in_(chIds)))
            await session.execute(delete(M3USource).where(M3USource.id == src.id))
            await session.commit()


@pytest.fixture
def svc(seededSource):
    return ChannelsManagementService()


async def _getChannelRow(pk):
    sm = DatabaseManager.get_sessionmaker()
    async with sm() as session:
        return await session.get(Channel, pk)


async def _mutateChannel(pk, **attrs):
    sm = DatabaseManager.get_sessionmaker()
    async with sm() as session:
        ch = await session.get(Channel, pk)
        assert ch is not None
        for k, v in attrs.items():
            setattr(ch, k, v)
        await session.commit()


async def _mutateFeeds(channelPk, **attrs):
    sm = DatabaseManager.get_sessionmaker()
    async with sm() as session:
        from sqlalchemy import select
        feeds = (await session.execute(select(Feed).where(Feed.channel_id == channelPk))).scalars().all()
        for f in feeds:
            for k, v in attrs.items():
                setattr(f, k, v)
        await session.commit()


class TestChannelsManagementIntegration:
    async def testGetAllChannelsReturnsMappedModels(self, svc):
        models = await svc.getAllChannels()
        assert len(models) >= 3
        first = models[0]
        assert first.channelId > 0
        assert first.displayName
        # At least one channel should have a logo (sample data varies)
        assert any(m.logoUrl for m in models)
        assert first.isLive is True
        assert isinstance(first.visitCount, int)
        assert isinstance(first.isFavorite, bool)

    async def testCountsConsistent(self, svc):
        allCount = await svc.getAllChannelsCount()
        listCount = len(await svc.getAllChannels())
        filteredCount = await svc.getChannelsCount(None)
        assert allCount == listCount == filteredCount

    async def testPaginationSlices(self, svc):
        allModels = await svc.getAllChannels()
        page1 = await svc.getChannelsPage(offset=0, limit=2)
        assert len(page1) == min(2, len(allModels))
        assert [m.displayName for m in page1] == [m.displayName for m in allModels[:2]]
        page2 = await svc.getChannelsPage(offset=100, limit=50)
        assert page2 == []

    async def testRecentlyAddedIncludesFreshImports(self, svc):
        recent = await svc.getRecentlyAddedChannels(limit=30)
        assert len(recent) >= 3

    async def testToggleFavoriteFlipCycle(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId

        newState = await svc.toggleFavorite(pk)
        assert newState is not None
        row = await _getChannelRow(pk)
        assert row.is_favorite == newState

        newState2 = await svc.toggleFavorite(pk)
        assert newState2 is not newState
        row2 = await _getChannelRow(pk)
        assert row2.is_favorite == newState2

        assert await svc.toggleFavorite(999999) is False

    async def testIncrementVisitCount(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId
        before = (await _getChannelRow(pk)).visit_count

        await svc.incrementVisitCount(pk)
        after = (await _getChannelRow(pk)).visit_count
        assert after == before + 1

        await svc.incrementVisitCount(999999)

    async def testTopChannelsByVisitCountOrdersDesc(self, svc):
        models = await svc.getAllChannels()
        assert len(models) >= 2
        a, b = models[0].channelId, models[1].channelId
        await _mutateChannel(a, visit_count=5)
        await _mutateChannel(b, visit_count=9)

        top = await svc.getTopChannelsByVisitCount(limit=2)
        assert len(top) == 2
        assert top[0].channelId == b
        assert top[1].channelId == a

    async def testGetM3uUrlsBasic(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId

        urls = await svc.getM3uUrls(pk)
        assert len(urls) >= 1
        assert urls[0].startswith("http")

        assert await svc.getM3uUrls(999999) == []

    async def testUpdateChannelReachabilityNormalizedVariant(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId

        row = await _getChannelRow(pk)
        assert row.m3u_provided_uris
        storedUrl = row.m3u_provided_uris[0]["url"]
        # Service normalizes both sides; pass normalized key
        from bingr.common.commonUtils import normalizeUrl
        normalizedKey = normalizeUrl(storedUrl)
        # Also verify a case-variant normalizes to same
        variant = storedUrl.replace("http://", "HTTP://").replace("example.com", "EXAMPLE.COM")
        assert normalizeUrl(variant) == normalizedKey

        updated = await svc.updateChannelReachability(pk, {normalizedKey: False})
        assert updated is True

        rowAfter = await _getChannelRow(pk)
        assert rowAfter.m3u_provided_uris[0]["reachable"] is False

        urlsAfter = await svc.getM3uUrls(pk)
        assert storedUrl not in urlsAfter

        # Restore for subsequent tests
        await svc.updateChannelReachability(pk, {normalizedKey: True})

    async def testUpdateChannelReachabilityUnknownId(self, svc):
        assert await svc.updateChannelReachability(999999, {}) is False

    async def testGetM3uStreamsWithMetaMatchesUrls(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId

        streams = await svc.getM3uStreamsWithMeta(pk)
        urls = await svc.getM3uUrls(pk)
        assert len(streams) == len(urls)
        for i, s in enumerate(streams):
            assert s.url == urls[i]
            assert s.name.startswith("Stream ")

        assert await svc.getM3uStreamsWithMeta(999999) == []

    async def testDistinctCategoriesSorted(self, svc):
        cats = await svc.getDistinctCategories()
        assert isinstance(cats, list)
        assert cats == sorted(cats)

    async def testHasUncategorizedChannels(self, svc):
        models = await svc.getAllChannels()
        assert len(models) >= 1
        pk = models[-1].channelId

        # Force one channel to have no categories
        await _mutateChannel(pk, categories=None)
        assert await svc.hasUncategorizedChannels() is True

        # Set it back
        await _mutateChannel(pk, categories=[{"name": "News"}])
        assert await svc.hasUncategorizedChannels() is False

    async def testCategoryFilterRoundtrip(self, svc):
        cats = await svc.getDistinctCategories()
        assert len(cats) >= 1
        target = cats[0]

        page = await svc.getChannelsPage(filters={"category": target}, limit=50)
        count = await svc.getChannelsCount({"category": target})
        assert len(page) == count
        assert all(target in (m.category or "") for m in page)

    async def testUncategorizedPseudoFilter(self, svc):
        models = await svc.getAllChannels()
        pk = models[-1].channelId
        await _mutateChannel(pk, categories=None)

        page = await svc.getChannelsPage(filters={"category": "uncategorized"}, limit=50)
        assert len(page) >= 1
        assert all(not m.category or m.category == "Uncategorized" for m in page)

        await _mutateChannel(pk, categories=[{"name": "News"}])

    async def testFavoriteFilter(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId
        await _mutateChannel(pk, is_favorite=False)
        await _mutateChannel(models[1].channelId, is_favorite=True)

        page = await svc.getChannelsPage(filters={"favorite": True}, limit=50)
        assert len(page) == 1
        assert page[0].channelId == models[1].channelId

    async def testSearchFilterCaseInsensitive(self, svc):
        models = await svc.getAllChannels()
        targetName = models[0].displayName.lower()
        assert "arte" in targetName or "bht" in targetName

        sub = "arte" if "arte" in targetName else "bht"
        page = await svc.getChannelsPage(filters={"search": sub}, limit=50)
        assert len(page) >= 1
        assert any(sub in (m.displayName or "").lower() for m in page)

    async def testQualityFilter(self, svc):
        models = await svc.getAllChannels()
        pk = models[0].channelId
        await _mutateFeeds(pk, format="1080p")

        page = await svc.getChannelsPage(filters={"quality": "FHD"}, limit=50)
        assert len(page) >= 1
        assert any(m.channelId == pk for m in page)
        matching = next(m for m in page if m.channelId == pk)
        assert matching.quality == "FHD"

    async def testCountryFilter(self, svc):
        countries = await svc.getDistinctCountries()
        assert len(countries) >= 1
        code, _ = countries[0]

        page = await svc.getChannelsPage(filters={"country": code}, limit=50)
        count = await svc.getChannelsCount({"country": code})
        assert len(page) == count
        assert all(m.countryCode.upper() == code.upper() for m in page)

    async def testTopCategoryNamesBoostAndLimit(self, svc):
        top = await svc.getTopCategoryNames(limit=2)
        assert len(top) <= 2

        cats = await svc.getDistinctCategories()
        if len(cats) > 2:
            boosted = await svc.getTopCategoryNames(limit=1, boost_names=[cats[0]], min_boost_count=1)
            assert boosted[0] == cats[0]

    async def testDistinctCountriesSortedByName(self, svc):
        countries = await svc.getDistinctCountries()
        names = [name for _, name in countries]
        assert names == sorted(names, key=str.lower)
        for code, _ in countries:
            assert code.isupper()

    async def testGetChannelsByCategory(self, svc):
        cats = await svc.getDistinctCategories()
        assert len(cats) >= 1
        target = cats[0]

        channels = await svc.getChannelsByCategory(target, limit=50)

        assert len(channels) >= 1
        assert all(target in (m.category or "") for m in channels)
        assert channels == sorted(channels, key=lambda m: m.displayName or "")

    async def testUpdateChannelReachabilityFeedStreams(self, svc):
        models = await svc.getAllChannels()
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from bingr.common.commonUtils import normalizeUrl

        async def _channelWithFeeds(pk):
            sm = DatabaseManager.get_sessionmaker()
            async with sm() as session:
                stmt = select(Channel).options(selectinload(Channel.feeds)).where(Channel.id == pk)
                return (await session.execute(stmt)).scalar_one()

        target = None
        for m in models:
            row = await _channelWithFeeds(m.channelId)
            for feed in row.feeds or []:
                if feed.streams:
                    target = (m.channelId, feed, feed.streams[0])
                    break
            if target:
                break
        if not target:
            pytest.skip("no channel with feed streams in seeded data")

        pk, feed, stream = target
        url = stream["url"]
        normalizedKey = normalizeUrl(url)

        updated = await svc.updateChannelReachability(pk, {normalizedKey: False})
        assert updated is True

        rowAfter = await _channelWithFeeds(pk)
        feedAfter = next(f for f in rowAfter.feeds if f.id == feed.id)
        assert feedAfter.streams[0]["reachable"] is False

        # Restore for subsequent tests
        await svc.updateChannelReachability(pk, {normalizedKey: True})
