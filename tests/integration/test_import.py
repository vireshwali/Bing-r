import pytest
from sqlalchemy import select

from bingr.common.exceptions import (
    DownloadError,
    MissingSourceParamsError,
    ProcessingError,
    SourceAlreadyImportedError,
)
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, M3UChannel, M3USource
from bingr.services.importerService import importM3u

pytestmark = pytest.mark.asyncio


async def testImportM3uToDb(cfg, dbSessionmaker, sample_m3u, tmp_path):
    m3u_copy = tmp_path / "import_test.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())
    source = await importM3u(
        sourceName="test",
        m3uPath=m3u_copy,
        config=cfg,
    )

    assert source.name == "test"
    assert source.channel_count is not None and source.channel_count > 0
    assert source.input_file is not None

    async with DatabaseManager.get_sessionmaker()() as session:
        srcCount = (await session.execute(select(M3USource))).scalar()
        assert srcCount is not None
        assert srcCount.id == source.id

        channels = (await session.execute(select(Channel))).scalars().all()
        assert len(channels) == source.channel_count


async def testImportDuplicateRejected(cfg, dbSessionmaker, sample_m3u, tmp_path):
    m3u_copy = tmp_path / "dup_test.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())

    await importM3u(
        sourceName="dup_test",
        m3uPath=m3u_copy,
        config=cfg,
    )

    with pytest.raises(SourceAlreadyImportedError, match="already imported"):
        await importM3u(
            sourceName="dup_test2",
            m3uPath=m3u_copy,
            config=cfg,
        )


async def test_import_corrupt_m3u_skips_bad_entries(cfg, dbSessionmaker, sampleCorrupt, tmp_path):
    m3u_copy = tmp_path / "corrupt_test.m3u"
    m3u_copy.write_bytes(sampleCorrupt.read_bytes())
    source = await importM3u(
        sourceName="corrupt_test",
        m3uPath=m3u_copy,
        config=cfg,
    )

    assert source.name == "corrupt_test"
    assert source.channel_count == 1

    async with DatabaseManager.get_sessionmaker()() as session:
        srcStored = (await session.execute(select(M3USource).where(M3USource.id == source.id))).scalar_one()
        assert srcStored.channel_count == 1


async def testImportFromUrl(cfg, dbSessionmaker, sample_m3u, tmp_path, mocker):
    m3u_content = sample_m3u.read_bytes()

    mockResp = mocker.Mock()
    mockResp.content = m3u_content
    mockResp.raise_for_status.return_value = None

    mocker.patch("httpx.Client.get", return_value=mockResp)

    source = await importM3u(
        sourceName="url_test",
        url="https://example.com/playlist.m3u",
        config=cfg,
    )

    assert source.name == "url_test"
    assert source.input_url == "https://example.com/playlist.m3u"
    assert source.channel_count is not None and source.channel_count > 0

    async with DatabaseManager.get_sessionmaker()() as session:
        srcStored = (await session.execute(select(M3USource).where(M3USource.id == source.id))).scalar_one()
        assert srcStored.channel_count == source.channel_count

        # ── Merge & EPG header tests ──────────────────────────────────────────────────


async def testImportMergeFileThenUrl(cfg, dbSessionmaker, sample_m3u, sampleMerge, tmp_path, mocker):
    m3u_copy = tmp_path / "merge_file.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())
    await importM3u(sourceName="merge_file_url", m3uPath=m3u_copy, config=cfg)

    mockResp = mocker.Mock()
    mockResp.content = sampleMerge.read_bytes()
    mockResp.raise_for_status.return_value = None
    mocker.patch("httpx.Client.get", return_value=mockResp)

    src2 = await importM3u(sourceName="merge_file_url", url="https://example.com/merge_file_url.m3u", config=cfg)
    assert src2.channel_count == 1

    async with DatabaseManager.get_sessionmaker()() as session:
        bht1 = (await session.execute(select(Channel).where(Channel.channel_id == "BHT1.ba"))).scalar_one()
        assert len(bht1.m3u_provided_uris) == 2

        arte = (await session.execute(select(Channel).where(Channel.channel_id == "ARTE.fr"))).scalar_one()
        assert any("FHD" in t for t in arte.tvg_names)

        newCc = (await session.execute(select(Channel).where(Channel.channel_id == "NEW.cc"))).scalar_one_or_none()
        assert newCc is not None

        src2_ch_ids = (
            (await session.execute(select(Channel.channel_id).join(M3UChannel).where(M3UChannel.source_id == src2.id)))
            .scalars()
            .all()
        )
        assert "BHT1.ba" in src2_ch_ids
        assert "ARTE.fr" in src2_ch_ids
        assert "NEW.cc" in src2_ch_ids


async def testImportMergeUrlThenFile(cfg, dbSessionmaker, sample_m3u, sampleMerge, tmp_path, mocker):
    mockResp = mocker.Mock()
    mockResp.content = sampleMerge.read_bytes()
    mockResp.raise_for_status.return_value = None
    mocker.patch("httpx.Client.get", return_value=mockResp)

    await importM3u(sourceName="merge_url_file", url="https://example.com/merge_url_file.m3u", config=cfg)

    m3u_copy = tmp_path / "merge_url_file.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())
    src2 = await importM3u(sourceName="merge_url_file", m3uPath=m3u_copy, config=cfg)
    assert src2.channel_count == 1

    async with DatabaseManager.get_sessionmaker()() as session:
        bht1 = (await session.execute(select(Channel).where(Channel.channel_id == "BHT1.ba"))).scalar_one()
        assert len(bht1.m3u_provided_uris) == 2

        arte = (await session.execute(select(Channel).where(Channel.channel_id == "ARTE.fr"))).scalar_one()
        assert any("FHD" in t for t in arte.tvg_names)

        src2_ch_ids = (
            (await session.execute(select(Channel.channel_id).join(M3UChannel).where(M3UChannel.source_id == src2.id)))
            .scalars()
            .all()
        )
        assert "BHT1.ba" in src2_ch_ids
        assert "ARTE.fr" in src2_ch_ids


async def testImportEpgHeaderStored(cfg, dbSessionmaker, sample_m3u, tmp_path):
    m3u_copy = tmp_path / "epg_test.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())
    source = await importM3u(sourceName="epg_test", m3uPath=m3u_copy, config=cfg)

    async with DatabaseManager.get_sessionmaker()() as session:
        stored = (await session.execute(select(M3USource).where(M3USource.id == source.id))).scalar_one()
        assert stored.m3u_provided_epg_url is not None
        assert "epg.example.com" in stored.m3u_provided_epg_url

        # ── File path edge cases ──────────────────────────────────────────────────────


async def testImportFileInPlaylistsDir(cfg, dbSessionmaker, sample_m3u):
    playlistsDir = cfg.workspacePath() / "playlists"
    playlistsDir.mkdir(parents=True, exist_ok=True)
    inPlace = playlistsDir / "in_place_test.m3u"
    inPlace.write_bytes(sample_m3u.read_bytes())
    source = await importM3u(sourceName="in_place", m3uPath=inPlace, config=cfg)
    assert source.channel_count > 0


async def testImportFileNonexistent(cfg, dbSessionmaker, tmp_path):
    bogus = tmp_path / "nonexistent.m3u"
    with pytest.raises(ProcessingError):
        await importM3u(sourceName="bogus", m3uPath=bogus, config=cfg)


async def testImportNoParams(cfg, dbSessionmaker):
    with pytest.raises(MissingSourceParamsError):
        await importM3u(sourceName="no_params", config=cfg)


async def testImportFileNoExtension(cfg, dbSessionmaker, sample_m3u, tmp_path):
    noExt = tmp_path / "noext_file"
    noExt.write_bytes(sample_m3u.read_bytes())
    source = await importM3u(sourceName="no_ext", m3uPath=noExt, config=cfg)
    assert source.channel_count > 0

    # ── URL edge cases ────────────────────────────────────────────────────────────


async def testImportUrlDownloadFails(cfg, dbSessionmaker, mocker):
    mocker.patch("httpx.Client.get", side_effect=Exception("Connection refused"))
    with pytest.raises(DownloadError):
        await importM3u(sourceName="dl_fail", url="https://example.com/fail.m3u", config=cfg)


async def testImportUrlSameUrlTwice(cfg, dbSessionmaker, sample_m3u, mocker):
    mockResp = mocker.Mock()
    mockResp.content = sample_m3u.read_bytes()
    mockResp.raise_for_status.return_value = None
    mocker.patch("httpx.Client.get", return_value=mockResp)

    await importM3u(sourceName="dup_url_a", url="https://example.com/dup.m3u", config=cfg)

    with pytest.raises(SourceAlreadyImportedError):
        await importM3u(sourceName="dup_url_b", url="https://example.com/dup.m3u", config=cfg)


async def testImportUrlNoPath(cfg, dbSessionmaker, sample_m3u, mocker):
    mockResp = mocker.Mock()
    mockResp.content = sample_m3u.read_bytes()
    mockResp.raise_for_status.return_value = None
    mocker.patch("httpx.Client.get", return_value=mockResp)

    source = await importM3u(sourceName="no_path", url="https://example.com", config=cfg)
    assert source.channel_count > 0

    # ── Empty / edge content tests ────────────────────────────────────────────────


async def testImportEmptyPlaylist(cfg, dbSessionmaker, sampleEmpty, tmp_path):
    m3u_copy = tmp_path / "empty.m3u"
    m3u_copy.write_bytes(sampleEmpty.read_bytes())
    source = await importM3u(sourceName="empty", m3uPath=m3u_copy, config=cfg)
    assert source.channel_count == 0


async def testImportAllSegmentsNoUri(cfg, dbSessionmaker, sampleNoUri, tmp_path):
    m3u_copy = tmp_path / "no_uri.m3u"
    m3u_copy.write_bytes(sampleNoUri.read_bytes())
    source = await importM3u(sourceName="no_uri", m3uPath=m3u_copy, config=cfg)
    assert source.channel_count == 0


async def testImportUnexpectedErrorWrapped(cfg, dbSessionmaker, sample_m3u, tmp_path, mocker):
    m3u_copy = tmp_path / "unexpected.m3u"
    m3u_copy.write_bytes(sample_m3u.read_bytes())
    mocker.patch("m3u8.load", side_effect=ValueError("corrupted"))
    with pytest.raises(ProcessingError) as exc:
        await importM3u(sourceName="unexpected", m3uPath=m3u_copy, config=cfg)
    assert exc.value.reason == "unexpected_error"
