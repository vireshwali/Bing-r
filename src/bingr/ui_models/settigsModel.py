from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SettingsModel:
    # -----------General Settings-----------
    hideNotWorkingChannelsWithOneFeed: bool = False

    # -----------Advacned Settings-----------
    # max value allowed is 24. Min allowed is 8
    homeScreenContinueWatchingChannelsSize: int = 15
    homeScreenContinueWatchingChannelsAutoScrollDelaySeconds: float = 4

    homeScreenCategory1ChannelsSize: int = 15
    homeScreenCategory1ChannelsAutoScrollDelaySeconds: float = 5

    homeScreenCategory2ChannelsSize: int = 20
    homeScreenCategory2ChannelsAutoScrollDelaySeconds: float = 5

    homeScreenCategory3ChannelsSize: int = 20
    homeScreenCategory3ChannelsAutoScrollDelaySeconds: float = 6

    homeScreenCategory4ChannelsSize: int = 20
    homeScreenCategory4ChannelsAutoScrollDelaySeconds: float = 6

    homeScreenRecentlyAddedChannelsSize: int = 32
    homeScreenRecentlyAddedChannelsAutoScrollDelaySeconds: float = 7
