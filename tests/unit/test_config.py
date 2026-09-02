import time
from pathlib import Path
from typing import Any

import pytest

from bingr.common.cache import MemoryCache
from bingr.common.config import _infer


class TestMemoryCache:
    def testGetSet(self):
        c = MemoryCache(ttl=300)
        c.set("key1", "val1")
        assert c.get("key1") == "val1"

    def testGetMissing(self):
        c = MemoryCache(ttl=300)
        assert c.get("nosuch") is None

    def testExpired(self):
        c = MemoryCache(ttl=0.01)
        c.set("key1", "val1")
        time.sleep(0.02)
        assert c.get("key1") is None

    def testDisabledReturnsNone(self):
        c = MemoryCache(ttl=0)
        assert c.get("key1") is None

    def testDisabledDoesNotStore(self):
        c = MemoryCache(ttl=0)
        c.set("key1", "val1")
        assert c._store == {}

    def testInvalidate(self):
        c = MemoryCache(ttl=300)
        c.set("key1", "val1")
        c.invalidate("key1")
        assert c.get("key1") is None

    def testClear(self):
        c = MemoryCache(ttl=300)
        c.set("key1", "val1")
        c.set("key2", "val2")
        c.clear()
        assert c.get("key1") is None
        assert c.get("key2") is None

    def testExpiredAutoPrunes(self):
        c = MemoryCache(ttl=0.01)
        c.set("key1", "val1")
        time.sleep(0.02)
        c.get("key1")
        assert "key1" not in c._store


class TestInfer:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            pytest.param("true", True, id="true"),
            pytest.param("TRUE", True, id="TRUE"),
            pytest.param("false", False, id="false"),
            pytest.param("FALSE", False, id="FALSE"),
        ],
    )
    def testBool(self, raw: str, expected: bool):
        assert _infer(raw) is expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            pytest.param("42", 42, id="positive"),
            pytest.param("-1", -1, id="negative"),
            pytest.param("0", 0, id="zero"),
        ],
    )
    def testInt(self, raw: str, expected: int):
        result = _infer(raw)
        assert result == expected
        assert isinstance(result, int)

    def testFloat(self):
        result = _infer("3.14")
        assert result == 3.14
        assert isinstance(result, float)

    def testPathTilde(self):
        result = _infer("~/foo/bar")
        assert isinstance(result, Path)
        assert str(result).startswith(str(Path.home()))

    def testPathAbsolute(self):
        result = _infer("/etc/bingr")
        assert isinstance(result, Path)
        assert str(result) == "/etc/bingr"

    def testFallbackString(self):
        assert _infer("hello world") == "hello world"

    def testEmptyString(self):
        assert _infer("") == ""


class TestConfig:
    @pytest.fixture(autouse=True)
    def _resetSingleton(self):
        import bingr.common.config as cfgMod

        cfgMod._config_instance = None
        yield

    @pytest.fixture
    def emptyShipped(self, tmp_path: Path) -> Path:
        p = tmp_path / "shipped.env"
        p.write_text("")
        return p

    @pytest.fixture
    def cfg(self, monkeypatch: Any, tmp_path: Path, emptyShipped: Path) -> Any:
        from bingr.common.config import Config

        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        return Config()

    def testLoadsShippedValues(self, monkeypatch: Any, tmp_path: Path):
        from bingr.common.config import Config

        shipped = tmp_path / "shipped.env"
        shipped.write_text("foo.bar=42\nbaz.qux=hello")
        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: shipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        c = Config()
        assert c.get("foo.bar") == 42
        assert c.get("baz.qux") == "hello"

    def testGetMissingDefault(self, cfg: Any):
        assert cfg.get("nosuch.key") is None
        assert cfg.get("nosuch.key", "fallback") == "fallback"

    def testGetInt(self, cfg: Any):
        cfg.set("test.count", "42")
        assert cfg.getInt("test.count") == 42

    def testGetIntDefault(self, cfg: Any):
        assert cfg.getInt("nosuch", 10) == 10

    def testGetIntInvalid(self, cfg: Any):
        cfg.set("test.bad", "notanumber")
        assert cfg.getInt("test.bad", 5) == 5

    def testGetBoolTrue(self, cfg: Any):
        cfg.set("test.flag", "true")
        assert cfg.getBool("test.flag") is True

    def testGetBoolFalse(self, cfg: Any):
        cfg.set("test.flag", "false")
        assert cfg.getBool("test.flag") is False

    def testGetBoolDefault(self, cfg: Any):
        assert cfg.getBool("nosuch", True) is True
        assert cfg.getBool("nosuch") is False

    def testGetBoolInvalid(self, cfg: Any):
        cfg.set("test.bad", "maybe")
        assert cfg.getBool("test.bad", True) is True

    def testSetStoresValue(self, cfg: Any):
        cfg.set("my.key", "myval")
        assert cfg.get("my.key") == "myval"

    def testSetPersistWritesDotenv(self, cfg: Any, tmp_path: Path):
        envFile = tmp_path / "test.env"
        envFile.write_text("")
        from bingr.common.config import Config

        c = Config(dotenvPath=envFile)
        c.set("persist.key", "persist_val", persist=True)
        content = envFile.read_text()
        assert "persist.key" in content
        assert "persist_val" in content

    def testEnvOverride(self, monkeypatch: Any, emptyShipped: Path):
        from bingr.common.config import Config

        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        monkeypatch.setenv("test.db.path", "env_value")
        c = Config()
        assert c.get("test.db.path") == "env_value"

    def testUserDotenvLoaded(self, monkeypatch: Any, tmp_path: Path, emptyShipped: Path):
        from bingr.common.config import Config

        userEnv = tmp_path / "user.env"
        userEnv.write_text("user.custom=from_user")
        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [userEnv])
        c = Config()
        assert c.get("user.custom") == "from_user"

    def testUserDotenvSkippedIfNotExists(self, monkeypatch: Any, emptyShipped: Path):
        from bingr.common.config import Config

        missing = Path("/tmp/nonexistent_bingr_test/.env")
        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [missing])
        Config()

    def testDotenvPathArg(self, monkeypatch: Any, tmp_path: Path, emptyShipped: Path):
        from bingr.common.config import Config

        extra = tmp_path / "extra.env"
        extra.write_text("extra.key=extra_val")
        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        c = Config(dotenvPath=extra)
        assert c.get("extra.key") == "extra_val"

    def testDotenvPathMissing(self, monkeypatch: Any, emptyShipped: Path):
        from bingr.common.config import Config

        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: emptyShipped)
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        c = Config(dotenvPath="/tmp/no_such_bingr_file_xyz/.env")
        assert c is not None


class TestGetConfig:
    @pytest.fixture(autouse=True)
    def _reset(self):
        import bingr.common.config as cfgMod

        cfgMod._config_instance = None
        yield

    def testGetConfigSingleton(self):
        from bingr.common.config import getConfig

        c1 = getConfig()
        c2 = getConfig()
        assert c1 is c2

    def testGetConfigWithDotenvPath(self, monkeypatch: Any, tmp_path: Path):
        from bingr.common.config import getConfig

        monkeypatch.setattr("bingr.common.config._resolveShippedDotenv", lambda: tmp_path / "empty.env")
        monkeypatch.setattr("bingr.common.config._getDefaultDotenvLocations", lambda: [])
        c = getConfig()
        assert c is not None
