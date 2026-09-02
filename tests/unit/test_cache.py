import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from bingr.common.cache import FileDataCache, initialize
from bingr.common.config import Config
from bingr.common.constants import API_FILES


@pytest.fixture
def cfg(tmp_path, mocker):
    c = Config()
    ws = tmp_path / "ws"
    mocker.patch.object(Config, "dataDir", return_value=ws)
    mocker.patch("bingr.common.cache.getConfig", return_value=c)
    return c


@pytest.fixture
def apiDir(cfg):
    d = cfg.workspacePath() / "api"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestFileDataCache:
    def testDownloadRaisesOnHttpError(self, cfg, mocker):
        cache = FileDataCache()
        url = "https://example.com/nonexistent.json"
        path = Path("/tmp/nonexistent_bingr_test.json")
        mocker.patch("httpx.Client.get", side_effect=Exception("Connection refused"))

        with pytest.raises(Exception, match="Connection refused"):
            cache._download(url, path)

    def testEnsureDownloadsStaleFile(self, cfg, apiDir, mocker):
        localName, url = API_FILES["channels"]
        fixturePath = apiDir / localName
        fixturePath.write_text("[]")
        oldTs = (datetime.now() - timedelta(days=30)).timestamp()
        os.utime(str(fixturePath), (oldTs, oldTs))

        cache = FileDataCache()
        mockDownload = mocker.patch.object(cache, "_download")
        cache.ensure("channels")
        mockDownload.assert_called_once_with(url, fixturePath)

    def testEnsureSkipsFreshFile(self, cfg, apiDir, mocker):
        localName, _url = API_FILES["channels"]
        fixturePath = apiDir / localName
        fixturePath.write_text("[]")

        cache = FileDataCache()
        mockDownload = mocker.patch.object(cache, "_download")
        cache.ensure("channels")
        mockDownload.assert_not_called()

    def testLoadMissingFileReturnsEmpty(self, cfg):
        cache = FileDataCache()
        result = cache.load("channels")
        assert result == []

    def testLoadCorruptFileReturnsEmpty(self, cfg, apiDir):
        localName = API_FILES["channels"][0]
        fixturePath = apiDir / localName
        fixturePath.write_text("not valid json")

        cache = FileDataCache()
        result = cache.load("channels")
        assert result == []


class TestInitialize:
    @pytest.fixture(autouse=True)
    def _resetFlag(self):
        import bingr.common.cache as cacheMod

        cacheMod._initialized = False
        yield

    def testInitializeIsIdempotent(self, cfg, mocker):
        mockMkdir = mocker.patch("pathlib.PosixPath.mkdir")
        mockGetMemory = mocker.patch("bingr.common.cache.getMemoryCache")
        mockGetFile = mocker.patch("bingr.common.cache.getFileCache")

        initialize(cfg)
        initialize(cfg)

        assert mockGetMemory.call_count == 1
        assert mockGetFile.call_count == 1
        assert mockMkdir.call_count == 1
