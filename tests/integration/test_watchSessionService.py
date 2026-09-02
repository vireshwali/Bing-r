import pytest

from bingr.services.importerService import importM3u
from bingr.services.libraryService import LibraryService
from bingr.services.watchSessionService import WatchSessionService

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
async def clearWatchSessions(dbSessionmaker):
    from sqlalchemy import delete

    from bingr.db.models import WatchSession

    async with dbSessionmaker() as session:
        await session.execute(delete(WatchSession))
        await session.commit()
    yield


@pytest.fixture(scope="module")
async def seededChannels(cfg, dbSessionmaker, tmp_path_factory):
    src = FIXTURES_DIR / "sample.m3u"
    m3u_copy = tmp_path_factory.mktemp("watch") / "sample.m3u"
    m3u_copy.write_bytes(src.read_bytes())
    await importM3u(
        sourceName="watch_test",
        m3uPath=m3u_copy,
        config=cfg,
    )
    channels = await LibraryService().listChannels()
    return [c.id for c in channels[:3]]


async def testRecordSessionPersists(seededChannels):
    service = WatchSessionService()
    pks = seededChannels
    ws = await service.recordSession(
        channelPk=pks[0],
        startedAt="2026-08-05T10:00:00",
        endedAt="2026-08-05T10:30:00",
        durationSeconds=1800,
        completed=True,
    )
    assert ws.id is not None
    assert ws.channel_id == pks[0]
    assert ws.duration_seconds == 1800
    assert ws.completed is True
    assert await service.countSessions() == 1


async def testRecordMultipleSessionsAccumulate(seededChannels):
    service = WatchSessionService()
    pks = seededChannels
    await service.recordSession(pks[0], "2026-08-05T10:00:00", "2026-08-05T10:10:00", 600, True)
    await service.recordSession(pks[1], "2026-08-05T11:00:00", "2026-08-05T11:05:00", 300, True)
    await service.recordSession(pks[0], "2026-08-05T12:00:00", "2026-08-05T12:20:00", 1200, True)
    assert await service.countSessions() == 3


async def testGetContinueWatchingChannelsOrdersByLatestSession(seededChannels):
    service = WatchSessionService()
    pks = seededChannels
    await service.recordSession(pks[0], "2026-08-05T10:00:00", "2026-08-05T10:10:00", 600, True)
    await service.recordSession(pks[1], "2026-08-05T11:00:00", "2026-08-05T11:05:00", 300, True)

    recent = await service.getContinueWatchingChannels(limit=2)
    assert len(recent) == 2
    assert recent[0].channelId == pks[1]
    assert recent[1].channelId == pks[0]


async def testGetContinueWatchingChannelsExcludesUnwatched(seededChannels):
    service = WatchSessionService()
    pks = seededChannels
    await service.recordSession(pks[0], "2026-08-05T10:00:00", "2026-08-05T10:10:00", 600, True)

    recent = await service.getContinueWatchingChannels(limit=10)
    assert {c.channelId for c in recent} == {pks[0]}


async def testGetTopChannelsByWatchTime(seededChannels):
    service = WatchSessionService()
    pks = seededChannels
    await service.recordSession(pks[0], "2026-08-05T10:00:00", "2026-08-05T10:30:00", 1800, True)
    await service.recordSession(pks[1], "2026-08-05T11:00:00", "2026-08-05T11:10:00", 600, True)
    await service.recordSession(pks[0], "2026-08-05T12:00:00", "2026-08-05T12:20:00", 1200, True)

    top = await service.getTopChannelsByWatchTime(limit=2)
    assert len(top) == 2
    channel0, total0 = top[0]
    channel1, total1 = top[1]
    assert channel0.id == pks[0]
    assert total0 == 3000
    assert channel1.id == pks[1]
    assert total1 == 600
