from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChannelDataModel:
    channelId: int
    displayName: str
    logoUrl: str
    countryCode: str
    countryName: str = ""
    category: str = ""
    quality: str = ""
    resolution: str = ""
    feedCount: int = 0
    isFavorite: bool = False
    isLive: bool = True
    websiteUrl: str = ""
    visitCount: int = 0
    languages: str = ""
    altNames: str = ""
    additionalTags: str = ""
