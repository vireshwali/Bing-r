from types import SimpleNamespace

from bingr.common.cache import getFileCache
from bingr.services.helpers.enrichmentHelper import (
    enrichSegment,
    ensureAllCaches,
    isCountryName,
    lookupChannel,
    lookupFeeds,
    lookupStreams,
    matchFeed,
)


def testEnsureAllCachesUsesBundledFixtures(cfg):
    getFileCache().clear()
    ensureAllCaches()
    assert lookupChannel("BHT1.ba") is not None
    assert lookupChannel("ARTE.fr") is not None
    feeds = lookupFeeds("BHT1.ba")
    assert len(feeds) == 2
    streams = lookupStreams("BHT1.ba", "HD")
    assert len(streams) >= 1


def testLookupChannelBht(cfg):
    getFileCache().clear()
    ensureAllCaches()
    ch = lookupChannel("BHT1.ba")
    assert ch is not None
    assert ch["name"] == "BHT 1"
    assert ch["website"] == "https://bht.ba"


def testLookupChannelArte(cfg):
    getFileCache().clear()
    ensureAllCaches()
    ch = lookupChannel("ARTE.fr")
    assert ch is not None
    assert ch["name"] == "ARTE"


def testLookupFeedsBht(cfg):
    getFileCache().clear()
    ensureAllCaches()
    feeds = lookupFeeds("BHT1.ba")
    assert len(feeds) == 2
    feedIds = {f["id"] for f in feeds}
    assert feedIds == {"HD", "SD"}


def testLookupStreamsBhtHd(cfg):
    getFileCache().clear()
    ensureAllCaches()
    streams = lookupStreams("BHT1.ba", "HD")
    assert len(streams) >= 1
    assert streams[0]["quality"] == "1080p"


def testIsCountryNameWithRealData(cfg):
    getFileCache().clear()
    ensureAllCaches()
    assert isCountryName("BA") is True
    assert isCountryName("FR") is True
    assert isCountryName("XX") is False


def testMatchFeedBhtHdSuffix(cfg):
    getFileCache().clear()
    ensureAllCaches()
    feeds = lookupFeeds("BHT1.ba")
    result = matchFeed("BHT1.ba@HD", feeds)
    assert result is not None
    assert result["format"] == "1080p"


def testMatchFeedBhtSdSuffix(cfg):
    getFileCache().clear()
    ensureAllCaches()
    feeds = lookupFeeds("BHT1.ba")
    result = matchFeed("BHT1.ba@SD", feeds)
    assert result is not None
    assert result["format"] == "576i"


def testEnrichSegmentBhtHd(cfg):
    getFileCache().clear()
    ensureAllCaches()

    seg = SimpleNamespace(
        title="BHT 1",
        uri="http://example.com/bht1.m3u8",
        duration=-1,
    )
    seg.custom_parser_values = {
        "extra": {
            "raw_title": "BHT 1 (1080p)",
            "resolution": None,
            "flags": [],
            "extinf_props": {
                "tvg-id": "BHT1.ba@HD",
                "tvg-name": "BHT 1 HD",
                "group-title": "BA",
            },
        }
    }

    result = enrichSegment(seg)
    assert result["tvg_id"] == "BHT1.ba@HD"
    assert result["display_name"] == "BHT 1 HD"
    assert result["clean_title"] == "BHT 1"
    assert result["country"]["code"] == "BA"
    assert result["matched_feed_id"] == "HD"
    assert len(result["feeds"]) == 2


def testEnrichSegmentArte(cfg):
    getFileCache().clear()
    ensureAllCaches()

    seg = SimpleNamespace(
        title="ARTE",
        uri="http://example.com/arte.m3u8",
        duration=-1,
    )
    seg.custom_parser_values = {
        "extra": {
            "raw_title": "ARTE",
            "resolution": None,
            "flags": [],
            "extinf_props": {
                "tvg-id": "ARTE.fr",
                "tvg-name": "ARTE HD",
                "group-title": "FR",
            },
        }
    }

    result = enrichSegment(seg)
    assert result["tvg_id"] == "ARTE.fr"
    assert result["country"]["code"] == "FR"
    assert result["matched_feed_id"] == "HD"


def testEnrichSegmentNoTvgIdFallback(cfg):
    getFileCache().clear()
    ensureAllCaches()

    seg = SimpleNamespace(
        title="Local Channel",
        uri="http://example.com/local.m3u8",
        duration=-1,
    )
    seg.custom_parser_values = {
        "extra": {
            "raw_title": "Local Channel",
            "resolution": None,
            "flags": [],
            "extinf_props": {},
        }
    }

    result = enrichSegment(seg)
    assert result["tvg_id"] == ""
    assert "feeds" not in result
