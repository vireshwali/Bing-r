"""Unit tests for the public importM3u pipeline — file handling and DB writes.

``m3u8.load``, enrichment (``enrichSegment``/``resolveChannelId``) and the DB
session are mocked; the copy-to-workspace logic, the channel upsert/merge logic
and the error paths (already-imported, missing params, download failure) run
for real.
"""

from types import SimpleNamespace

import pytest

from bingr.common.exceptions import DownloadError, MissingSourceParamsError, SourceAlreadyImportedError
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel
from bingr.services import importerService as importer_module
from bingr.services.importerService import importM3u


class FakeCfg:
    def __init__(self, workspace):
        self._workspace = workspace

    def workspacePath(self):
        return self._workspace

    def getInt(self, key, default):
        return default


class ImportM3uTestBase:
    @pytest.fixture
    def cfg(self, tmp_path):
        return FakeCfg(tmp_path)

    @pytest.fixture
    def sessionMaker(self, mocker):
        # A plain MagicMock result, so its children (scalar_one_or_none etc.)
        # stay sync mocks instead of AsyncMock children.
        result = mocker.MagicMock()
        # Default: no existing M3USource / channel / M3UChannel rows.
        result.scalar_one_or_none.return_value = None

        session = mocker.MagicMock()
        session.execute = mocker.AsyncMock(return_value=result)
        session.add = mocker.MagicMock()
        session.flush = mocker.AsyncMock()
        session.commit = mocker.AsyncMock()

        sm = mocker.MagicMock()
        sm.return_value.__aenter__ = mocker.AsyncMock(return_value=session)
        sm.return_value.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=sm)
        return sm, session

    @pytest.fixture
    def importerMocks(self, mocker, cfg):
        mocker.patch.object(importer_module, "getConfig", return_value=cfg)
        mocker.patch.object(importer_module, "ensureAllCaches")
        mocker.patch.object(importer_module, "isCountryName", return_value=False)

    @staticmethod
    def _enriched(tvg_id, title, uri):
        return {
            "tvg_id": tvg_id,
            "group_title": "News",
            "uri": uri,
            "title": title,
            "clean_title": title,
            "tvg_name": "",
            "display_name": title,
            "raw_title": title,
            "resolution": "720p",
            "flags": [],
            "duration": 10,
            "tvg_logo": "",
            "country": None,
            "feeds": [],
        }

    @staticmethod
    def _fakePlaylist(segmentCount):
        return SimpleNamespace(data={}, segments=[object() for _ in range(segmentCount)])

    @staticmethod
    def _m3uFile(tmp_path, name="my_playlist.m3u"):
        path = tmp_path / name
        path.write_text("#EXTM3U\n")
        return path


class TestImportFromFile(ImportM3uTestBase):
    async def testCopiesFileAndPersistsChannels(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(2))
        mocker.patch.object(
            importer_module,
            "enrichSegment",
            side_effect=[
                self._enriched("one.us", "Channel One", "https://a.com/1.m3u8"),
                self._enriched("two.us", "Channel Two", "https://a.com/2.m3u8"),
            ],
        )
        mocker.patch.object(importer_module, "resolveChannelId", side_effect=["one.us", "two.us"])
        src_file = self._m3uFile(tmp_path)

        source = await importM3u("unit_test", m3uPath=src_file, config=cfg)

        assert source.name == "unit_test"
        assert source.channel_count == 2
        assert source.input_file == str(src_file)
        _sm, session = sessionMaker
        session.commit.assert_awaited_once()

        addedChannels = [c for c in session.add.call_args_list if isinstance(c.args[0], Channel)]
        assert len(addedChannels) == 2
        assert {c.args[0].channel_id for c in addedChannels} == {"one.us", "two.us"}

        # The playlist was copied into the workspace playlists dir.
        copied = list((cfg.workspacePath() / "playlists").glob("my_playlist_*.m3u"))
        assert len(copied) == 1
        assert copied[0].read_text() == "#EXTM3U\n"

    async def testFileAlreadyInPlaylistsDirNotCopied(self, mocker, cfg, sessionMaker, importerMocks):
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(1))
        mocker.patch.object(importer_module, "enrichSegment", return_value=self._enriched("one.us", "One", "https://a.com/1.m3u8"))
        mocker.patch.object(importer_module, "resolveChannelId", return_value="one.us")
        playlists = cfg.workspacePath() / "playlists"
        playlists.mkdir(parents=True)
        src_file = playlists / "existing.m3u"
        src_file.write_text("#EXTM3U\n")

        source = await importM3u("unit_test", m3uPath=src_file, config=cfg)

        assert source.path == str(src_file)
        assert list(playlists.glob("existing_*.m3u")) == []  # no timestamped copy

    async def testDuplicateChannelMergedNotRecounted(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(2))
        mocker.patch.object(
            importer_module,
            "enrichSegment",
            side_effect=[
                self._enriched("one.us", "Channel One", "https://a.com/1.m3u8"),
                self._enriched("one.us", "Channel One Alt", "https://a.com/2.m3u8"),
            ],
        )
        mocker.patch.object(importer_module, "resolveChannelId", side_effect=["one.us", "one.us"])

        existing = SimpleNamespace(
            id=5,
            m3u_provided_uris=[],
            tvg_ids=[],
            titles=[],
            clean_titles=[],
            tvg_names=[],
            group_titles=[],
            tvg_logos=[],
            resolutions=[],
            flags=[],
            categories=[],
            updated_at="old",
        )
        mocker.patch.object(
            importer_module,
            "_findChannel",
            new=mocker.AsyncMock(side_effect=[None, existing]),
        )
        src_file = self._m3uFile(tmp_path, "merge.m3u")

        source = await importM3u("unit_test", m3uPath=src_file, config=cfg)

        assert source.channel_count == 1  # second segment merged, not counted
        assert existing.m3u_provided_uris == [{"url": "https://a.com/2.m3u8", "reachable": True}]
        assert existing.tvg_ids == ["one.us"]
        assert existing.updated_at != "old"


class TestImportErrors(ImportM3uTestBase):
    async def testRaisesSourceAlreadyImported(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        _sm, session = sessionMaker
        session.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(id=9, name="old")
        src_file = self._m3uFile(tmp_path, "dup.m3u")

        with pytest.raises(SourceAlreadyImportedError):
            await importM3u("unit_test", m3uPath=src_file, config=cfg)

    async def testRaisesMissingSourceParams(self, mocker, cfg, importerMocks):
        with pytest.raises(MissingSourceParamsError):
            await importM3u("unit_test", config=cfg)

    async def testDownloadFailureRaisesDownloadError(self, mocker, cfg, importerMocks):
        client = mocker.patch.object(importer_module.httpx, "Client")
        client.side_effect = RuntimeError("connection failed")

        with pytest.raises(DownloadError):
            await importM3u("unit_test", url="https://example.com/playlist.m3u8", config=cfg)

    async def testUnexpectedErrorWrappedInProcessingError(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        _sm, session = sessionMaker
        session.commit.side_effect = RuntimeError("db exploded")
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(1))
        mocker.patch.object(importer_module, "enrichSegment", return_value=self._enriched("one.us", "One", "https://a.com/1.m3u8"))
        mocker.patch.object(importer_module, "resolveChannelId", return_value="one.us")
        src_file = self._m3uFile(tmp_path)

        with pytest.raises(importer_module.ProcessingError):
            await importM3u("unit_test", m3uPath=src_file, config=cfg)


class TestImportSegmentEdgeCases(ImportM3uTestBase):
    async def testEnrichFailureSkipsSegmentAndCountsRest(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(2))
        mocker.patch.object(
            importer_module,
            "enrichSegment",
            side_effect=[
                RuntimeError("enrich boom"),
                self._enriched("one.us", "One", "https://a.com/1.m3u8"),
            ],
        )
        mocker.patch.object(importer_module, "resolveChannelId", return_value="one.us")
        src_file = self._m3uFile(tmp_path)

        source = await importM3u("unit_test", m3uPath=src_file, config=cfg)

        # The failing segment was skipped; only the good one counted.
        assert source.channel_count == 1
        _sm, session = sessionMaker
        addedChannels = [c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], Channel)]
        assert len(addedChannels) == 1

    async def testSegmentWithoutUriSkipped(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(1))
        mocker.patch.object(
            importer_module,
            "enrichSegment",
            return_value=self._enriched("one.us", "One", ""),
        )
        mocker.patch.object(importer_module, "resolveChannelId", return_value="one.us")
        src_file = self._m3uFile(tmp_path)

        source = await importM3u("unit_test", m3uPath=src_file, config=cfg)

        assert source.channel_count == 0
        _sm, session = sessionMaker
        addedChannels = [c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], Channel)]
        assert addedChannels == []

    async def testFeedWithoutIdNotInserted(self, mocker, cfg, sessionMaker, importerMocks, tmp_path):
        from bingr.db.models import Feed

        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(1))
        enriched = self._enriched("one.us", "One", "https://a.com/1.m3u8")
        enriched["feeds"] = [
            {"name": "missing-id-feed"},
            {"id": "feed-1", "name": "Good Feed", "streams": [{"url": "https://f.com/1"}]},
        ]
        mocker.patch.object(importer_module, "enrichSegment", return_value=enriched)
        mocker.patch.object(importer_module, "resolveChannelId", return_value="one.us")
        src_file = self._m3uFile(tmp_path)

        await importM3u("unit_test", m3uPath=src_file, config=cfg)

        _sm, session = sessionMaker
        addedFeeds = [c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], Feed)]
        assert len(addedFeeds) == 1
        assert addedFeeds[0].feed_id == "feed-1"
        assert addedFeeds[0].streams == [{"url": "https://f.com/1", "reachable": True}]

    async def testUrlDownloadWritesPlaylistToDisk(self, mocker, cfg, sessionMaker, importerMocks):
        clientInst = mocker.MagicMock()
        clientInst.get.return_value = SimpleNamespace(content=b"#EXTM3U\n")
        mocker.patch.object(importer_module.httpx, "Client", return_value=clientInst)
        mocker.patch.object(importer_module.m3u8, "load", return_value=self._fakePlaylist(0))

        url = "https://example.com/live/playlist.m3u8"
        source = await importM3u("unit_test", url=url, config=cfg)

        clientInst.get.assert_called_once()
        assert source.input_url == url
        downloaded = list((cfg.workspacePath() / "playlists").glob("playlist_*.m3u8"))
        assert len(downloaded) == 1
        assert downloaded[0].read_bytes() == b"#EXTM3U\n"
