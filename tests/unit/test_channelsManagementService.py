"""Unit tests for ChannelsManagementService — pure/static helpers and query logic."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bingr.db.dbManager import DatabaseManager
from bingr.services.channelsManagementService import ChannelsManagementService as Cms


@pytest.fixture
def svc(mocker):
    mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=MagicMock())
    return Cms()


@pytest.fixture
def dbSession(mocker):
    """A mocked async sessionmaker whose execute returns a configurable result."""
    result = mocker.MagicMock()
    session = mocker.MagicMock()
    session.execute = mocker.AsyncMock(return_value=result)
    sm = mocker.MagicMock()
    sm.return_value.__aenter__ = mocker.AsyncMock(return_value=session)
    sm.return_value.__aexit__ = mocker.AsyncMock(return_value=False)
    mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=sm)
    return session, result


class TestCountChannelsPerCategory:
    async def testCountsDictEntriesByName(self, dbSession):
        _session, result = dbSession
        result.scalars.return_value.all.return_value = [
            [{"name": "News"}, {"name": "Sports"}],
            [{"name": "News"}],
            "not-a-list",
            [{"name": 42}, "not-a-dict", {"id": "no-name"}],
        ]

        svc = Cms()
        counts = await svc._countChannelsPerCategory()

        assert counts == {"News": 2, "Sports": 1}

    async def testEmptyRows(self, dbSession):
        _session, result = dbSession
        result.scalars.return_value.all.return_value = []

        assert await Cms()._countChannelsPerCategory() == {}


class TestGetTopCategoryNames:
    @pytest.fixture
    def svc(self, mocker):
        mocker.patch.object(DatabaseManager, "get_sessionmaker", return_value=MagicMock())
        return Cms()

    def _counts(self):
        return {
            "News": 10, "Movies": 9, "Sports": 8, "Kids": 7, "Music": 6,
            "Drama": 5, "Comedy": 4, "Action": 3, "SciFi": 2, "Doc": 1,
        }

    async def testFewerThanLimitReturnsAll(self, svc, mocker):
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value={"A": 5, "B": 3}))
        assert await svc.getTopCategoryNames(limit=4) == ["A", "B"]

    async def testExactlyLimitReturnsAll(self, svc, mocker):
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value={"A": 5, "B": 3}))
        assert await svc.getTopCategoryNames(limit=2) == ["A", "B"]

    async def testBoostPromotedAheadOfRanking(self, svc, mocker):
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value=self._counts()))

        result = await svc.getTopCategoryNames(limit=3, boost_names=["Movies", "Music"], min_boost_count=6)

        assert result[:2] == ["Movies", "Music"]
        assert len(result) == 3

    async def testBoostBelowMinCountNotPromoted(self, svc, mocker):
        counts = dict(self._counts())
        counts["Music"] = 3  # below min_boost_count
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value=counts))

        result = await svc.getTopCategoryNames(limit=3, boost_names=["Music"], min_boost_count=6)

        assert "Music" not in result
        assert result == ["News", "Movies", "Sports"]

    async def testBoostMatchCaseInsensitive(self, svc, mocker):
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value=self._counts()))

        result = await svc.getTopCategoryNames(limit=3, boost_names=["movies"], min_boost_count=6)

        assert result[0] == "Movies"  # canonical name returned

    async def testNoBoostMatchKeepsRanking(self, svc, mocker):
        mocker.patch.object(svc, "_countChannelsPerCategory", new=mocker.AsyncMock(return_value=self._counts()))

        result = await svc.getTopCategoryNames(limit=3, boost_names=["Nonexistent"], min_boost_count=6)

        assert result == ["News", "Movies", "Sports"]


class TestGetM3uStreamsWithMeta:
    def _channel(self, **overrides):
        attrs = dict(
            id=1,
            feeds=[],
            m3u_provided_uris=[],
        )
        attrs.update(overrides)
        return SimpleNamespace(**attrs)

    def _feed(self, streams, languages=None):
        return SimpleNamespace(streams=streams, languages=languages, format=None)

    async def testChannelNotFound(self, dbSession):
        _session, result = dbSession
        result.scalar_one_or_none.return_value = None

        assert await Cms().getM3uStreamsWithMeta(999) == []

    async def testBuildsOrderedStreamsFromM3uThenFeeds(self, dbSession):
        _session, result = dbSession
        channel = self._channel(
            m3u_provided_uris=[
                {"url": "https://m.com/1.m3u8", "reachable": True},
                {"url": "https://m.com/2.m3u8", "reachable": False},
                "legacy-str",
            ],
            feeds=[
                self._feed(
                    [
                        {"url": "https://f.com/1.m3u8", "reachable": True},
                        {"url": "https://f.com/2.m3u8", "reachable": False},
                    ],
                    languages=[{"code": "eng"}],
                ),
            ],
        )
        result.scalar_one_or_none.return_value = channel

        streams = await Cms().getM3uStreamsWithMeta(1)

        assert [s.url for s in streams] == [
            "https://m.com/1.m3u8",
            "legacy-str",
            "https://f.com/1.m3u8",
        ]
        assert streams[0].name == "Stream 1 (EN)"
        assert streams[0].langCode == "EN"

    async def testFeedStreamDedupedAgainstM3uUrl(self, dbSession):
        _session, result = dbSession
        channel = self._channel(
            m3u_provided_uris=[{"url": "https://f.com/1.m3u8/", "reachable": True}],
            feeds=[
                self._feed(
                    [{"url": "https://f.com/1.m3u8", "reachable": True}],
                    languages=None,
                ),
            ],
        )
        result.scalar_one_or_none.return_value = channel

        streams = await Cms().getM3uStreamsWithMeta(1)

        # Trailing-slash variant is deduped: only the m3u URL survives.
        assert [s.url for s in streams] == ["https://f.com/1.m3u8/"]


class TestGetM3uUrls:
    def _feed(self, streams, languages=None):
        return SimpleNamespace(streams=streams, languages=languages, format=None)

    async def testChannelNotFound(self, dbSession):
        _session, result = dbSession
        result.scalar_one_or_none.return_value = None

        assert await Cms().getM3uUrls(999) == []

    async def testFeedStreamUrlsAppendedAfterM3uUrls(self, dbSession):
        _session, result = dbSession
        channel = SimpleNamespace(
            id=1,
            m3u_provided_uris=[{"url": "https://m.com/1.m3u8", "reachable": True}],
            feeds=[
                self._feed(
                    [{"url": "https://f.com/1.m3u8", "reachable": True}],
                    languages=[{"code": "eng"}],
                ),
            ],
        )
        result.scalar_one_or_none.return_value = channel

        urls = await Cms().getM3uUrls(1)

        assert urls == ["https://m.com/1.m3u8", "https://f.com/1.m3u8"]

    async def testUnreachableM3uUriExcluded(self, dbSession):
        _session, result = dbSession
        channel = SimpleNamespace(
            id=2,
            m3u_provided_uris=[
                {"url": "https://dead.com/x.m3u8", "reachable": False},
                {"url": "https://alive.com/y.m3u8", "reachable": True},
            ],
            feeds=[],
        )
        result.scalar_one_or_none.return_value = channel

        assert await Cms().getM3uUrls(2) == ["https://alive.com/y.m3u8"]


class TestUpdateChannelReachabilityUnit:
    async def testFeedWithoutStreamsIsSkipped(self, dbSession, mocker):
        _session, result = dbSession
        channel = SimpleNamespace(
            id=4,
            m3u_provided_uris=[{"url": "https://m.com/1.m3u8", "reachable": True}],
            feeds=[SimpleNamespace(streams=None, languages=None)],
        )
        result.scalar_one_or_none.return_value = channel

        session, _result = dbSession
        session.commit = mocker.AsyncMock()
        ok = await Cms().updateChannelReachability(4, {"https://m.com/1.m3u8": False})

        assert ok is True
        session.commit.assert_awaited_once()
        assert channel.m3u_provided_uris[0]["reachable"] is False

    async def testMissingChannelReturnsFalse(self, dbSession):
        _session, result = dbSession
        result.scalar_one_or_none.return_value = None

        assert await Cms().updateChannelReachability(999, {}) is False


class TestAggregateLanguages:
    def testMixedStrAndDictSortedDeduped(self, svc):
        feeds = [
            SimpleNamespace(languages=["eng", {"name": "German", "code": "deu"}, "", {"code": "bos"}]),
            SimpleNamespace(languages=["eng", "German"]),
        ]
        assert svc._aggregateLanguages(feeds) == "German, bos, eng"

    def testDictWithoutNameFallsBackToCode(self, svc):
        feeds = [SimpleNamespace(languages=[{"code": "spa"}])]
        assert svc._aggregateLanguages(feeds) == "spa"

    def testNonListLanguagesIgnored(self, svc):
        assert svc._aggregateLanguages([SimpleNamespace(languages=None)]) == ""
        assert svc._aggregateLanguages([SimpleNamespace(languages="eng")]) == ""

    def testEmptyFeeds(self, svc):
        assert svc._aggregateLanguages([]) == ""


class TestParseResolution:
    @pytest.mark.parametrize("raw,expected", [
        ("1080p", (1080, 1, "1080p")),
        ("1080i", (1080, 0, "1080i")),
        ("720", (720, 1, "720p")),
        (" 480i ", (480, 0, "480i")),
        ("abc", None),
        ("", None),
        ("1080x", None),
    ])
    def testParseResolution(self, svc, raw, expected):
        assert svc._parseResolution(raw) == expected


class TestNumericToQuality:
    @pytest.mark.parametrize("num,expected", [
        (240, "SD"), (360, "SD"), (480, "SD"), (540, "SD"), (576, "SD"),
        (720, "HD"),
        (1080, "FHD"),
        (1440, "QHD"),
        (2160, "4K"),
        (4320, "8K"),
        (999, ""),
    ])
    def testNumericToQuality(self, svc, num, expected):
        assert svc._numericToQuality(num) == expected


class TestExtractUriFromM3uItem:
    @pytest.mark.parametrize("item,expected", [
        ({"url": "https://example.com/a.m3u8"}, "https://example.com/a.m3u8"),
        ({}, ""),
        ({"url": ""}, ""),
        ("plain-string", "plain-string"),
        (42, ""),
    ])
    def testExtractUriFromM3uItem(self, svc, item, expected):
        assert Cms._extractUriFromM3uItem(item) == expected


class TestIterFeedStreams:
    def testYieldsUrlLangPairsSkipsUnreachableAndSeen(self, svc):
        feed = SimpleNamespace(
            languages=[{"code": "eng"}],
            format=None,
            streams=[
                {"url": "https://a.com/1.m3u8", "reachable": True},
                {"url": "https://a.com/1.m3u8/", "reachable": True},
                {"url": "https://a.com/2.m3u8", "reachable": False},
                {"url": "https://a.com/3.m3u8", "reachable": True},
                "not-a-dict",
                {"reachable": True},
                {"url": 123, "reachable": True},
            ],
        )
        seen = set()
        results = list(Cms._iterFeedStreams([feed], seen))
        assert results == [
            ("https://a.com/1.m3u8", "EN"),
            ("https://a.com/3.m3u8", "EN"),
        ]
        assert seen == {"https://a.com/1.m3u8", "https://a.com/3.m3u8"}

    def testEmptyFeeds(self, svc):
        assert list(Cms._iterFeedStreams([], set())) == []
        assert list(Cms._iterFeedStreams([SimpleNamespace(streams=None, format=None, languages=None)], set())) == []


class TestExtractLangCode:
    @pytest.mark.parametrize("languages,expected", [
        (None, ""),
        ([], ""),
        ([{}], ""),
        ([{"code": "eng"}], "EN"),
        ([{"code": "en"}], "EN"),
        (["fre"], "FR"),
        ([" spa "], "ES"),
        (["xyz"], ""),
        ("not-a-list", ""),
        ([None], ""),
        ([{"name": "English"}], ""),
    ])
    def testExtractLangCode(self, svc, languages, expected):
        feed = SimpleNamespace(languages=languages) if languages is not None else SimpleNamespace(languages=None)
        assert Cms._extractLangCode(feed) == expected


class TestMakeStream:
    def testNoLangCode(self):
        s = Cms._makeStream(0, "https://u.com", "")
        assert s.name == "Stream 1"
        assert s.url == "https://u.com"
        assert s.langCode == ""

    def testWithLangCode(self):
        s = Cms._makeStream(2, "https://u.com", "EN")
        assert s.name == "Stream 3 (EN)"
        assert s.langCode == "EN"


class TestUpdateReachabilityItem:
    def testMatchingKeyUpdatesCopy(self, svc):
        item = {"url": "https://example.com/a.m3u8", "reachable": True}
        result = Cms._updateReachabilityItem(item, {"https://example.com/a.m3u8": False})
        assert result["reachable"] is False
        assert item["reachable"] is True
        assert result is not item

    def testHostCaseVariantMatches(self, svc):
        item = {"url": "https://Example.COM/a.m3u8", "reachable": True}
        result = Cms._updateReachabilityItem(item, {"https://example.com/a.m3u8": False})
        assert result["reachable"] is False

    def testUnmatchedReturnsSame(self):
        item = {"url": "https://a.com/x.m3u8", "reachable": True}
        result = Cms._updateReachabilityItem(item, {"https://b.com/y.m3u8": False})
        assert result is item

    def testNonDictReturnsSame(self):
        assert Cms._updateReachabilityItem("not-a-dict", {}) == "not-a-dict"

    def testDictWithoutUrlReturnsSame(self):
        item = {"reachable": True}
        assert Cms._updateReachabilityItem(item, {}) is item


class TestIterReachableM3uUrls:
    def testFiltersAndExtracts(self, svc):
        ch = SimpleNamespace(m3u_provided_uris=[
            {"url": "https://a.com/1.m3u8", "reachable": True},
            {"url": "https://a.com/2.m3u8", "reachable": False},
            "legacy-str",
            {"url": "", "reachable": True},
            {"url": "https://a.com/3.m3u8"},
        ])
        urls = list(Cms._iterReachableM3uUrls(ch))
        assert urls == ["https://a.com/1.m3u8", "legacy-str", "https://a.com/3.m3u8"]

    def testNoneInput(self, svc):
        assert list(Cms._iterReachableM3uUrls(SimpleNamespace(m3u_provided_uris=None))) == []


class TestIterReachableFeedUrls:
    def testFiltersFeedStreams(self, svc):
        feeds = [
            SimpleNamespace(streams=[
                {"url": "https://a.com/1.m3u8", "reachable": True},
                {"url": "https://a.com/2.m3u8", "reachable": False},
                "bad-entry",
            ], languages=None),
            SimpleNamespace(streams=None, languages=None),
        ]
        urls = list(Cms._iterReachableFeedUrls(feeds))
        assert urls == ["https://a.com/1.m3u8"]


class TestCountUniqueStreamUrls:
    def testDedupsAcrossM3uAndFeedsTrailingSlash(self, svc):
        ch = SimpleNamespace(
            m3u_provided_uris=[{"url": "https://a.com/1.m3u8/", "reachable": True}],
            feeds=[SimpleNamespace(streams=[{"url": "https://a.com/1.m3u8", "reachable": True}])],
        )
        assert Cms._countUniqueStreamUrls(ch, ch.feeds) == 1


class TestDetermineQualityAndResolution:
    def _ch(self, resolutions=None):
        return SimpleNamespace(resolutions=resolutions)

    def _feed(self, fmt):
        return SimpleNamespace(format=fmt)

    def testChannelResolutionsWins(self, svc):
        ch = self._ch(["1080p"])
        q, r = svc._determineQualityAndResolution([], ch)
        assert (q, r) == ("FHD", "1080p")

    def testFeedFormatMaps(self, svc):
        ch = self._ch([])
        q, r = svc._determineQualityAndResolution([self._feed("HD")], ch)
        assert (q, r) == ("HD", "720p")

    def testFeedFormatParsedDirectly(self, svc):
        ch = self._ch([])
        q, r = svc._determineQualityAndResolution([self._feed("1080i")], ch)
        assert (q, r) == ("FHD", "1080i")

    def testBestWinsOverMultipleSources(self, svc):
        ch = self._ch(["480p"])
        q, r = svc._determineQualityAndResolution([self._feed("2160p")], ch)
        assert (q, r) == ("4K", "2160p")

    def testProgressiveBeatsInterlacedSameNumber(self, svc):
        ch = self._ch(["1080i"])
        q, r = svc._determineQualityAndResolution([self._feed("1080p")], ch)
        assert (q, r) == ("FHD", "1080p")

    def testFallback(self, svc):
        ch = self._ch([])
        q, r = svc._determineQualityAndResolution([], ch)
        assert (q, r) == ("SD", "")


class TestMappers:
    def _mockChannel(self, **overrides):
        attrs = dict(
            id=7,
            display_name="Test Channel",
            canonical_name="canonical",
            channel_id="test.channel",
            tvg_logos=["https://logo.png"],
            country={"code": "ba", "name": "BiH"},
            categories=[{"name": "News"}, {"name": "Movies"}],
            alt_names=["Alt A", "Alt B"],
            flags=["censored", "geo-blocked"],
            website="https://site.example",
            visit_count=3,
            is_favorite=True,
            resolutions=["720p"],
            m3u_provided_uris=[],
            feeds=[],
        )
        attrs.update(overrides)
        # Ensure all feed objects have format=None (accessed by _collectFeedResolutions)
        feeds = attrs.get("feeds", [])
        for f in feeds:
            if not hasattr(f, "format"):
                f.format = None
        return SimpleNamespace(**attrs)

    def testMapChannelAllFields(self, svc):
        ch = self._mockChannel()
        m = svc.mapChannel(ch)

        assert m.channelId == 7
        assert m.displayName == "Test Channel"
        assert m.logoUrl == "https://logo.png"
        assert m.countryCode == "BA"
        assert m.category == "Movies, News"
        assert m.quality == "HD"
        assert m.resolution == "720p"
        assert m.feedCount == 0
        assert m.visitCount == 3
        assert m.isFavorite is True
        assert m.isLive is True
        assert m.websiteUrl == "https://site.example"
        assert m.languages == ""
        assert m.altNames == "Alt A, Alt B"
        assert m.additionalTags == "Censored, Geo Blocked"

    def testDisplayNameFallbacks(self, svc):
        ch = self._mockChannel(display_name=None, canonical_name="Fallback")
        m = svc.mapChannel(ch)
        assert m.displayName == "Fallback"
        ch = self._mockChannel(display_name=None, canonical_name=None, channel_id="last.resort")
        m = svc.mapChannel(ch)
        assert m.displayName == "last.resort"

    def testEmptyCollections(self, svc):
        ch = self._mockChannel(
            categories=None, alt_names=None, flags=None, tvg_logos=None, country=None, website=None
        )
        m = svc.mapChannel(ch)
        assert m.category == "Uncategorized"
        assert m.altNames == ""
        assert m.additionalTags == ""
        assert m.logoUrl == ""
        assert m.countryCode == ""
        assert m.websiteUrl == ""

    def testAggregateLanguages(self, svc):
        feeds = [
            SimpleNamespace(languages=["eng", {"name": "German", "code": "deu"}], format=None, streams=[]),
        ]
        ch = self._mockChannel(feeds=feeds)
        m = svc.mapChannel(ch)
        assert m.languages == "German, eng"

    def testResolveFirstWorkingLogo(self, svc):
        ch = self._mockChannel(tvg_logos=["https://logo.png"])
        assert svc._resolveFirstWorkingLogo(ch.tvg_logos) == "https://logo.png"
        assert svc._resolveFirstWorkingLogo(None) == ""
        assert svc._resolveFirstWorkingLogo([]) == ""

    def testExtractCountryCode(self, svc):
        assert svc._extractCountryCode(self._mockChannel()) == "BA"
        assert svc._extractCountryCode(self._mockChannel(country={"code": ""})) == ""
        assert svc._extractCountryCode(self._mockChannel(country=None)) == ""

    def testExtractCategory(self, svc):
        assert svc._extractCategory(self._mockChannel()) == "Movies, News"
        assert svc._extractCategory(self._mockChannel(categories=None)) == "Uncategorized"
        assert svc._extractCategory(self._mockChannel(categories=[{}])) == "Uncategorized"

    def testExtractAltNames(self, svc):
        assert svc._extractAltNames(self._mockChannel()) == "Alt A, Alt B"
        assert svc._extractAltNames(self._mockChannel(alt_names=None)) == ""
        assert svc._extractAltNames(self._mockChannel(alt_names=["", "valid", None])) == "valid"

    def testExtractFlags(self, svc):
        assert svc._extractFlags(self._mockChannel()) == "Censored, Geo Blocked"
        assert svc._extractFlags(self._mockChannel(flags=None)) == ""
        assert svc._extractFlags(self._mockChannel(flags=["single-flag"])) == "Single Flag"
