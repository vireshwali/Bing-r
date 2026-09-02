from pathlib import Path

import pytest

from bingr.services.settingsService import DEFAULT_VALUES, RESTART_REQUIRED_KEYS, SettingsService


class TestSettingsService:
    @pytest.fixture
    def service(self, tmp_path: Path) -> SettingsService:
        return SettingsService(settingsPath=tmp_path / "settings.conf")

    def testGetUnknownKeyReturnsDefault(self, service: SettingsService):
        assert service.get("nosuch/key") is None
        assert service.get("nosuch/key", "fallback") == "fallback"

    def testGetKnownDefault(self, service: SettingsService):
        assert service.get("general/language") == "system"
        assert service.get("playback/defaultVolume") == 50

    def testSetAndGet(self, service: SettingsService):
        service.set("general/language", "fr")
        assert service.get("general/language") == "fr"

    def testContains(self, service: SettingsService):
        assert not service.contains("general/language")
        service.set("general/language", "fr")
        assert service.contains("general/language")

    def testPersistsAcrossInstances(self, tmp_path: Path):
        path = tmp_path / "settings.conf"
        SettingsService(settingsPath=path).set("playback/volumeStep", 7)
        second = SettingsService(settingsPath=path)
        assert second.get("playback/volumeStep") == 7

    def testResetToDefaults(self, service: SettingsService):
        service.set("general/language", "fr")
        service.set("playback/defaultVolume", 80)
        service.resetToDefaults()
        assert not service.contains("general/language")
        assert not service.contains("playback/defaultVolume")

    def testRequiresRestartPositive(self, service: SettingsService):
        assert service.requiresRestart("playback/hwdec")

    def testRequiresRestartNegative(self, service: SettingsService):
        assert not service.requiresRestart("playback/defaultVolume")


class TestSettingsDefaults:
    def testAllRestartKeysAreKnownDefaults(self):
        assert RESTART_REQUIRED_KEYS.issubset(DEFAULT_VALUES.keys())

    def testEveryDefaultKeyHasSlashGroup(self):
        for key in DEFAULT_VALUES:
            assert "/" in key
            group, _name = key.split("/", 1)
            assert group in {
                "general",
                "playback",
                "network",
                "library",
                "epg",
                "appearance",
                "privacy",
                "advanced",
                "bingr",
            }
