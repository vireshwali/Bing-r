import os
import shutil
from pathlib import Path

import pytest

from bingr.common.cache import getFileCache
from bingr.common.cache import initialize as initCache
from bingr.common.config import Config, getConfig
from bingr.common.constants import API_FILES
from bingr.db.dbManager import DatabaseManager
from tests.conftest import RUNTIME_DIR, TESTS_ROOT

FIXTURES_DIR = TESTS_ROOT / "fixtures"
IPTV_DIR = FIXTURES_DIR / "iptv-org"


@pytest.fixture(scope="session")
def _testsRuntime():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


@pytest.fixture(scope="session")
def cfg(_testsRuntime):
    ws = _testsRuntime / "workspace"
    ws.mkdir(parents=True, exist_ok=True)

    originalDataDir = Config.dataDir

    def _testDataDir(self):
        return ws

    Config.dataDir = _testDataDir
    try:
        yield getConfig(dotenvPath=TESTS_ROOT / "config" / "test.env")
    finally:
        Config.dataDir = originalDataDir


@pytest.fixture(scope="session")
def initCacheFixture(cfg):
    initCache(cfg)


@pytest.fixture(autouse=True)
def clearCache():
    getFileCache().clear()


@pytest.fixture(scope="session", autouse=True)
def seedApiFixtures(cfg, initCacheFixture):
    apiDir = cfg.workspacePath() / "api"
    for _name, (localName, _url) in API_FILES.items():
        src = IPTV_DIR / localName
        if src.exists():
            shutil.copy(src, apiDir / localName)


@pytest.fixture(scope="session")
def alembicIni(_testsRuntime):
    projectRoot = TESTS_ROOT.parent
    src = projectRoot / "config" / "alembic.ini"
    dst = _testsRuntime / "config" / "alembic.ini"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return dst


@pytest.fixture(scope="session")
def sample_m3u() -> Path:
    return FIXTURES_DIR / "sample.m3u"


@pytest.fixture(scope="session")
def sampleCorrupt() -> Path:
    return FIXTURES_DIR / "sample_corrupt.m3u"


@pytest.fixture(scope="session")
def sampleEmpty() -> Path:
    return FIXTURES_DIR / "sample_empty.m3u"


@pytest.fixture(scope="session")
def sampleNoUri() -> Path:
    return FIXTURES_DIR / "sample_no_uri.m3u"


@pytest.fixture(scope="session")
def sampleMerge() -> Path:
    return FIXTURES_DIR / "sample_merge.m3u"


@pytest.fixture(scope="session")
def dbSessionmaker(cfg, alembicIni):
    dbPath = cfg.dbPath()
    dbPath.parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(dbPath):
        os.remove(dbPath)
    DatabaseManager.initialize(dbPath, alembicIniPath=str(alembicIni))
    yield DatabaseManager.get_sessionmaker()
    DatabaseManager.shutdownSync()
