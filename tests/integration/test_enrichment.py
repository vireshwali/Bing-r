"""Integration tests for enrichmentHelper against real iptv-org fixture data.

Uses the fixture files seeded into the test workspace by the integration
conftest (``seedApiFixtures``) so the full cache → lookup → match → expand
pipeline runs against realistic data, not the synthetic unit-test store.
"""

from types import SimpleNamespace

from bingr.services.helpers.enrichmentHelper import (
    enrichSegment,
    lookupFeeds,
    lookupStreams,
    matchFeed,
)


def _segment(rawTitle, tvgId, uri, tvgName=""):
    seg = SimpleNamespace(title=rawTitle, uri=uri, duration=-1.0)
    seg.custom_parser_values = {
        "extra": {
            "raw_title": rawTitle,
            "resolution": None,
            "flags": [],
            "extinf_props": {"tvg-id": tvgId, "tvg-name": tvgName},
        }
    }
    return seg


def testEnrichSegmentBhtAgainstRealData(seedApiFixtures, initCacheFixture, cfg):
    seg = _segment("BHT 1 HD", "BHT1.ba@HD", "http://example.com/bht1.m3u8", "BHT 1 HD")

    result = enrichSegment(seg)

    assert result["tvg_id"] == "BHT1.ba@HD"
    assert result["display_name"] == "BHT 1 HD"
    assert result["channel"]["name"] == "BHT 1"
    assert result["channel"]["website"] == "https://bht.ba"
    assert result["matched_feed_id"] == "HD"
    assert result["country"]["code"] == "BA"
    assert result["country"]["name"] == "Bosnia and Herzegovina"

    feeds = result["feeds"]
    assert len(feeds) == 2
    hdFeed = next(f for f in feeds if f["id"] == "HD")
    assert hdFeed["format"] == "1080p"
    assert hdFeed["streams"][0]["url"] == "http://example.com/bht1.m3u8"
    assert hdFeed["streams"][0]["quality"] == "1080p"


def testEnrichSegmentArteAgainstRealData(seedApiFixtures, initCacheFixture, cfg):
    seg = _segment("ARTE HD", "ARTE.fr@HD", "http://example.com/arte.m3u8", "ARTE HD")

    result = enrichSegment(seg)

    assert result["tvg_id"] == "ARTE.fr@HD"
    assert result["matched_feed_id"] == "HD"
    assert result["channel"]["name"] == "ARTE"
    assert len(result["channel"]["categories"]) == 1
    assert result["channel"]["categories"][0]["name"] == "Culture"

    feeds = result["feeds"]
    assert len(feeds) == 1
    assert feeds[0]["streams"][0]["url"] == "http://example.com/arte.m3u8"


def testMatchFeedWithRealFeeds(seedApiFixtures, initCacheFixture, cfg):
    feeds = lookupFeeds("BHT1.ba")
    assert len(feeds) == 2

    assert matchFeed("BHT1.ba@HD", feeds)["id"] == "HD"
    assert matchFeed("BHT1.ba@SD", feeds)["id"] == "SD"
    assert matchFeed("BHT1.ba", feeds)["id"] == "HD"  # no suffix → is_main pick


def testLookupStreamsWithRealData(seedApiFixtures, initCacheFixture, cfg):
    streams = lookupStreams("BHT1.ba", "HD")
    assert len(streams) == 1
    assert streams[0]["quality"] == "1080p"

    assert lookupStreams("BHT1.ba", "8K") == []
    assert lookupStreams("nonexistent", "HD") == []
