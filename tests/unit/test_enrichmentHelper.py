"""Unit tests for enrichmentHelper — lookup, matching, expansion, and enrichment."""

import pytest

from bingr.common.constants import API_FILES
from bingr.services.helpers.enrichmentHelper import (
    _expandBroadcastArea,
    _expandCategories,
    _expandCity,
    _expandCountry,
    _expandLanguages,
    _expandRegion,
    _expandSubdivision,
    _pickMatchingStream,
    _scoreCandidates,
    _scoreFeed,
    _suffixMatchesFeedName,
    _suffixToFormat,
    _suffixToRegion,
    _tryPhase2,
    enrichSegment,
    ensureAllCaches,
    isCountryName,
    lookupChannel,
    lookupFeeds,
    lookupStreams,
    matchFeed,
    resolveChannelId,
)
from tests.unit._data import API_FEEDS
from tests.unit._data import segment as _segment


def testEnsureAllCachesCallsDownloadForEachApiFile(mocker):
    mockEnsure = mocker.patch("bingr.common.cache.FileDataCache.ensure")
    ensureAllCaches()
    assert mockEnsure.call_count == len(API_FILES)
    for name in API_FILES:
        mockEnsure.assert_any_call(name)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("BA", True, id="is_country_name_code_ba"),
        pytest.param("ba", True, id="is_country_name_code_lowercase"),
        pytest.param("Bosnia and Herzegovina", True, id="is_country_name_full"),
        pytest.param("bosnia and herzegovina", True, id="is_country_name_case_insensitive"),
        pytest.param("HR", True, id="is_country_name_code_hr"),
        pytest.param("Croatia", True, id="is_country_name_croatia"),
        pytest.param("Germany", False, id="is_country_name_not_found"),
        pytest.param("", False, id="is_country_name_empty"),
    ],
)
def testIsCountryName(value, expected, apiData):
    assert isCountryName(value) is expected


@pytest.mark.parametrize(
    ("tvgId", "expectedId", "expectedName"),
    [
        pytest.param("BHT1.ba", "BHT1.ba", "BHT 1", id="lookup_channel_exact"),
        pytest.param("BHT1.ba@HD", "BHT1.ba", "BHT 1", id="lookup_channel_with_suffix"),
    ],
)
def testLookupChannelFound(tvgId, expectedId, expectedName, apiData):
    result = lookupChannel(tvgId)
    assert result is not None
    assert result["id"] == expectedId
    assert result["name"] == expectedName


def testLookupChannelNotFound(apiData):
    assert lookupChannel("nonexistent") is None


def testLookupChannelEmpty(apiData):
    assert lookupChannel("") is None


def testLookupFeedsFound(apiData):
    result = lookupFeeds("BHT1.ba")
    assert len(result) == 2
    assert {f["id"] for f in result} == {"SD", "HD"}


def testLookupFeedsNotFound(apiData):
    assert lookupFeeds("nonexistent") == []


def testLookupFeedsEmpty(apiData):
    assert lookupFeeds("") == []


def testLookupStreamsFound(apiData):
    result = lookupStreams("BHT1.ba", "HD")
    assert len(result) == 1
    assert result[0]["quality"] == "1080p"


def testLookupStreamsNotFound(apiData):
    assert lookupStreams("BHT1.ba", "8K") == []


def testLookupStreamsNoFeedId(apiData):
    assert lookupStreams("BHT1.ba", None) == []


def testMatchFeedNoSuffixPicksIsMain(apiData):
    result = matchFeed("BHT1.ba", API_FEEDS)
    assert result is not None
    assert result["id"] == "HD"


def testMatchFeedSdSuffixMatchesSdFeed(apiData):
    result = matchFeed("BHT1.ba@SD", API_FEEDS)
    assert result is not None
    assert result["id"] == "SD"


def testMatchFeedHdSuffixMatchesHdFeed(apiData):
    result = matchFeed("BHT1.ba@HD", API_FEEDS)
    assert result is not None
    assert result["id"] == "HD"


def testMatchFeedNoFeedsReturnsNone():
    assert matchFeed("BHT1.ba", []) is None


def testEnrichSegmentNoTvgId():
    seg = _segment(rawTitle="No ID", extinfProps={})
    result = enrichSegment(seg)
    assert result["tvg_id"] == ""
    assert "feeds" not in result


def testEnrichSegmentTvgIdButChannelNotFound(apiData):
    seg = _segment(rawTitle="Unknown", extinfProps={"tvg-id": "unknown.ch"})
    result = enrichSegment(seg)
    assert result["tvg_id"] == "unknown.ch"
    assert "feeds" not in result


def testEnrichSegmentFull(apiData):
    seg = _segment(
        rawTitle="BHT 1 (1080p)",
        extinfProps={
            "tvg-id": "BHT1.ba@HD",
            "tvg-name": "BHT 1 HD",
            "group-title": "BA",
        },
    )
    result = enrichSegment(seg)
    assert result["tvg_id"] == "BHT1.ba@HD"
    assert result["display_name"] == "BHT 1 HD"
    assert result["clean_title"] == "BHT 1"
    assert result["uri"] == "http://example.com/stream"
    assert result["country"] == {"code": "BA", "name": "Bosnia and Herzegovina", "flag": ""}
    assert result["matched_feed_id"] is not None
    assert len(result.get("feeds", [])) == 2

    chData = result.get("channel", {})
    assert chData["name"] == "BHT 1"
    assert chData["website"] == "https://bht.ba"
    assert len(chData.get("categories", [])) == 1


def testEnrichSegmentWithTvgCountry(apiData):
    seg = _segment(
        rawTitle="BHT 1 HR",
        extinfProps={
            "tvg-id": "BHT1.ba",
            "tvg-country": "HR",
        },
    )
    result = enrichSegment(seg)
    assert result["country"] == {"code": "HR", "name": "Croatia", "flag": ""}


@pytest.mark.parametrize(
    ("enriched", "sourceName", "expected"),
    [
        pytest.param(
            {"tvg_id": "BHT1.ba@HD", "title": "BHT 1"},
            "iptv-org",
            "BHT1.ba",
            id="resolve_channel_id_with_tvg_id",
        ),
        pytest.param(
            {"tvg_id": "", "title": "Some Channel"},
            "test-src",
            "not_found_testsrc_some_channel",
            id="resolve_channel_id_generates_not_found",
        ),
        pytest.param(
            {"tvg_id": "  ", "title": "My Chan"},
            "src",
            "not_found_src_my_chan",
            id="resolve_channel_id_whitespace_tvg_id",
        ),
        pytest.param(
            {"tvg_id": "", "title": ""},
            "src",
            "not_found_src_",
            id="resolve_channel_id_empty_title",
        ),
    ],
)
def testResolveChannelId(enriched, sourceName, expected):
    assert resolveChannelId(sourceName, enriched) == expected

    # ── Expansion function tests ──────────────────────────────────


class TestExpandCountry:
    def testFound(self, apiData):
        result = _expandCountry("BA")
        assert result == {"code": "BA", "name": "Bosnia and Herzegovina", "flag": ""}

    def testCaseInsensitive(self, apiData):
        result = _expandCountry("ba")
        assert result == {"code": "BA", "name": "Bosnia and Herzegovina", "flag": ""}

    def testUkNormalizedToGb(self, apiData):
        result = _expandCountry("UK")
        assert result == {"code": "GB", "name": "United Kingdom", "flag": ""}

    def testUkLowercaseNormalizedToGb(self, apiData):
        result = _expandCountry("uk")
        assert result == {"code": "GB", "name": "United Kingdom", "flag": ""}

    def testNotFound(self, apiData):
        assert _expandCountry("XX") is None

    def testEmpty(self, apiData):
        assert _expandCountry("") is None


class TestExpandSubdivision:
    def testFound(self, apiData):
        result = _expandSubdivision("BA-BIH")
        assert result is not None
        assert result["name"] == "Federation of Bosnia and Herzegovina"

    def testNotFound(self, apiData):
        assert _expandSubdivision("ZZ-XXX") is None

    def testEmpty(self, apiData):
        assert _expandSubdivision("") is None


class TestExpandRegion:
    def testFound(self, apiData):
        result = _expandRegion("EU")
        assert result is not None
        assert result["name"] == "Europe"

    def testNotFound(self, apiData):
        assert _expandRegion("ZZ") is None

    def testEmpty(self, apiData):
        assert _expandRegion("") is None


class TestExpandCity:
    def testFound(self, apiData):
        result = _expandCity("Sarajevo")
        assert result is not None
        assert result["name"] == "Sarajevo"
        assert result["country"] == "BA"

    def testNotFound(self, apiData):
        assert _expandCity("Nowhere") is None

    def testEmpty(self, apiData):
        assert _expandCity("") is None


class TestExpandBroadcastArea:
    def testCountryPrefix(self, apiData):
        result = _expandBroadcastArea("c/BA")
        assert result is not None
        assert result["code"] == "BA"

    def testSubdivisionPrefix(self, apiData):
        result = _expandBroadcastArea("s/BA-BIH")
        assert result is not None
        assert result["name"] == "Federation of Bosnia and Herzegovina"

    def testRegionPrefix(self, apiData):
        result = _expandBroadcastArea("r/EU")
        assert result is not None
        assert result["name"] == "Europe"

    def testCityPrefix(self, apiData):
        result = _expandBroadcastArea("ct/Sarajevo")
        assert result is not None
        assert result["name"] == "Sarajevo"

    def testUnknownPrefix(self, apiData):
        assert _expandBroadcastArea("z/test") is None

    def testEmpty(self, apiData):
        assert _expandBroadcastArea("") is None

        # ── Additional feed matching edge cases ───────────────────────


class TestMatchFeed:
    def testMexicoSuffix(self):
        feeds = [
            {
                "id": "MX",
                "channel": "BHT1.ba",
                "name": "BHT 1 MX",
                "format": "SD",
                "is_main": False,
                "broadcast_area": ["c/MX"],
                "languages": ["spa"],
            },
            {
                "id": "BA",
                "channel": "BHT1.ba",
                "name": "BHT 1 BA",
                "format": "1080p",
                "is_main": True,
                "broadcast_area": ["c/BA"],
                "languages": ["bos"],
            },
        ]
        result = matchFeed("BHT1.ba@MEXICO", feeds)
        assert result is not None
        assert result["id"] == "MX"

    def testPanregionalSuffix(self):
        feeds = [
            {
                "id": "REG",
                "channel": "BHT1.ba",
                "name": "BHT 1 PanReg",
                "format": "SD",
                "is_main": False,
                "broadcast_area": ["r/"],
                "languages": ["eng"],
            },
            {
                "id": "BA",
                "channel": "BHT1.ba",
                "name": "BHT 1 BA",
                "format": "1080p",
                "is_main": True,
                "broadcast_area": ["c/BA"],
                "languages": ["bos"],
            },
        ]
        result = matchFeed("BHT1.ba@PANREGIONAL", feeds)
        assert result is not None
        assert result["id"] == "REG"

    def testPhase2Plus123Suffix(self):
        feeds = [
            {
                "id": "SD",
                "channel": "BHT1.ba",
                "name": "BHT 1 SD",
                "format": "576i",
                "is_main": False,
                "broadcast_area": ["c/BA"],
                "languages": ["bos"],
            },
            {
                "id": "HD",
                "channel": "BHT1.ba",
                "name": "BHT 1 HD",
                "format": "1080p",
                "is_main": True,
                "broadcast_area": ["c/BA"],
                "languages": ["bos"],
            },
        ]
        result = matchFeed("BHT1.ba@Plus123", feeds)
        assert result is not None

    def testAllFeedsScoreZero(self):
        feeds = [
            {
                "id": "F1",
                "channel": "BHT1.ba",
                "name": "Unrelated",
                "format": "unknown",
                "is_main": False,
                "broadcast_area": [],
                "languages": [],
            },
        ]
        result = matchFeed("BHT1.ba@HD", feeds)
        assert result is not None
        assert result["id"] == "F1"


class TestExpandCategories:
    def testPartialMatchReturnsFound(self, apiData):
        result = _expandCategories(["news", "nope"])
        assert result == [{"id": "news", "name": "News", "description": "News channels"}]

    def testEmpty(self, apiData):
        assert _expandCategories([]) == []


class TestExpandLanguages:
    def testPartialMatchReturnsFound(self, apiData):
        result = _expandLanguages(["bos", "zzz"])
        assert result == [{"code": "bos", "name": "Bosnian"}]

    def testEmpty(self, apiData):
        assert _expandLanguages([]) == []


class TestSuffixToFormat:
    @pytest.mark.parametrize(
        ("suffix", "expected"),
        [
            ("", None),
            ("HD", None),
            ("SD", None),
            ("1080P", "1080p"),
            ("1080I", "1080i"),
            ("720P", "720p"),
            ("576I", "576i"),
            ("480I", "480i"),
            ("PLUS1", None),
        ],
    )
    def testMapping(self, suffix, expected):
        assert _suffixToFormat(suffix) == expected


class TestSuffixToRegion:
    @pytest.mark.parametrize(
        ("suffix", "expected"),
        [
            ("", None),
            ("MEXICO", "c/MX"),
            ("mexico", "c/MX"),
            ("PANREGIONAL", "r/"),
            ("HD", None),
        ],
    )
    def testMapping(self, suffix, expected):
        assert _suffixToRegion(suffix) == expected


class TestSuffixMatchesFeedName:
    def testMatch(self):
        assert _suffixMatchesFeedName("hd", "BHT 1 HD") is True

    def testNoMatch(self):
        assert _suffixMatchesFeedName("sd", "BHT 1 HD") is False

    def testEmptySuffix(self):
        assert _suffixMatchesFeedName("", "BHT 1 HD") is False

    def testEmptyName(self):
        assert _suffixMatchesFeedName("hd", "") is False


class TestScoreFeed:
    @staticmethod
    def _feed(**overrides):
        attrs = dict(id="F1", name="BHT 1", format=None, is_main=False, broadcast_area=[])
        attrs.update(overrides)
        return attrs

    def testFormatMatchScoresThree(self):
        assert _scoreFeed(self._feed(format="1080p"), "HD", "1080p", None) == 3

    def testSdFallbackWhenNoFormatSuffix(self):
        assert _scoreFeed(self._feed(format="SD"), "HD", None, None) == 1

    def testRegionMatchScoresThree(self):
        feed = self._feed(broadcast_area=["c/MX", "c/BA"])
        assert _scoreFeed(feed, "MEXICO", None, "c/MX") == 3

    def testNameMatchScoresTwo(self):
        assert _scoreFeed(self._feed(name="BHT 1 HD"), "hd", None, None) == 2

    def testIsMainScoresOne(self):
        assert _scoreFeed(self._feed(is_main=True), "hd", None, None) == 1

    def testCombinedMaxScore(self):
        feed = self._feed(format="1080p", name="BHT 1 HD", is_main=True, broadcast_area=["c/BA"])
        assert _scoreFeed(feed, "hd", "1080p", None) == 3 + 2 + 1

    def testNoMatchScoresZero(self):
        assert _scoreFeed(self._feed(), "zzz", None, None) == 0


class TestScoreCandidates:
    def testSortsDescending(self):
        feeds = [
            {"id": "low", "name": "X", "format": "SD", "is_main": False, "broadcast_area": []},
            {"id": "high", "name": "Y HD", "format": "1080p", "is_main": True, "broadcast_area": ["c/BA"]},
        ]
        scored = _scoreCandidates(feeds, "HD", "1080p", None)
        assert [f["id"] for f, _s in scored] == ["high", "low"]
        assert scored[0][1] >= scored[1][1]

    def testEmpty(self):
        assert _scoreCandidates([], "HD", None, None) == []


class TestTryPhase2:
    @staticmethod
    def _feeds():
        return [
            {"id": "SD", "name": "BHT 1 SD", "format": "576i", "is_main": False, "broadcast_area": ["c/BA"]},
            {"id": "HD", "name": "BHT 1 HD", "format": "1080p", "is_main": True, "broadcast_area": ["c/BA"]},
        ]

    def testPlusSuffixWithBetterScoreReturnsFeed(self):
        result = _tryPhase2(self._feeds(), "Plus123", None, None, bestScore=0)
        assert result is not None
        assert result["id"] == "HD"

    def testPlusSuffixNotBetterThanBestScore(self):
        assert _tryPhase2(self._feeds(), "Plus123", None, None, bestScore=5) is None

    def testNonPlusSuffix(self):
        assert _tryPhase2(self._feeds(), "HD", None, None, bestScore=0) is None

    def testEmptySuffix(self):
        assert _tryPhase2(self._feeds(), "", None, None, bestScore=0) is None


class TestPickMatchingStream:
    def testExactUrlMatch(self):
        streams = [
            {"url": "http://example.com/stream", "quality": "1080p", "label": "HD"},
            {"url": "http://example.com/alt", "quality": "576i", "label": "SD"},
        ]
        result = _pickMatchingStream("http://example.com/stream", streams)
        assert result is not None
        assert result["quality"] == "1080p"

    def testPartialUrlMatch(self):
        streams = [
            {"url": "http://example.com/stream?token=abc", "quality": "1080p", "label": "HD"},
        ]
        result = _pickMatchingStream("http://example.com/stream?token=xyz", streams)
        assert result is not None
        assert result["quality"] == "1080p"

    def testNoMatch(self):
        streams = [
            {"url": "http://other.com/stream", "quality": "1080p", "label": "HD"},
        ]
        result = _pickMatchingStream("http://example.com/stream", streams)
        assert result is None

    def testEmptyUriReturnsNone(self):
        assert _pickMatchingStream("", [{"url": "http://x.com"}]) is None

    def testEmptyStreamsReturnsNone(self):
        assert _pickMatchingStream("http://x.com", []) is None
