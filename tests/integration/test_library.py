import pytest

from bingr.services.importerService import importM3u
from bingr.services.libraryService import LibraryService

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(scope="module")
async def seededLibrary(cfg, dbSessionmaker, tmp_path_factory):
    src = FIXTURES_DIR / "sample.m3u"
    m3u_copy = tmp_path_factory.mktemp("lib") / "sample.m3u"
    m3u_copy.write_bytes(src.read_bytes())

    await importM3u(
        sourceName="lib_test",
        m3uPath=m3u_copy,
        config=cfg,
    )
    return LibraryService()


async def testListSources(seededLibrary):
    sources = await seededLibrary.listSources()
    assert len(sources) >= 1
    assert any(s.name == "lib_test" for s in sources)


async def testListChannels(seededLibrary):
    channels = await seededLibrary.listChannels()
    assert len(channels) >= 2


async def testGetChannelById(seededLibrary):
    channels = await seededLibrary.listChannels()
    if channels:
        ch = await seededLibrary.getChannel(channels[0].channel_id)
        assert ch is not None
        assert ch.id == channels[0].id


async def testSearchChannels(seededLibrary):
    results = await seededLibrary.searchChannels("bht")
    assert len(results) >= 1
    assert any("bht" in r.display_name.lower() for r in results)


async def testSearchChannelsEmpty(seededLibrary):
    results = await seededLibrary.searchChannels("zzzznonexistent")
    assert len(results) == 0
