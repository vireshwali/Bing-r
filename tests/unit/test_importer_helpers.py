"""Unit tests for private helper functions in importerService."""

from bingr.services.importerService import (
    _findChannel,
    _markStreamsReachable,
    _mergeCategories,
    _mergeUniqueStr,
    _mergeUniqueUris,
)


class TestMergeUniqueStr:
    def testCaseSensitive(self):
        result = _mergeUniqueStr(["A", "b"], ["a"], caseSensitive=True)
        assert result == ["A", "b", "a"]

    def testCaseSensitiveDeduplicates(self):
        result = _mergeUniqueStr(["A", "b"], ["A", "b"], caseSensitive=True)
        assert result == ["A", "b"]

    def testCaseInsensitive(self):
        result = _mergeUniqueStr(["A", "b"], ["a"], caseSensitive=False)
        assert result == ["A", "b"]

    def testCaseInsensitiveEmptyNew(self):
        result = _mergeUniqueStr(["A", "b"], [], caseSensitive=False)
        assert result == ["A", "b"]

    def testExistingIsNone(self):
        result = _mergeUniqueStr(None, ["a", "b"], caseSensitive=True)
        assert result == ["a", "b"]


class TestMergeCategories:
    def testBasicMerge(self):
        existing = [{"id": "news"}, {"id": "sports"}]
        new = [{"id": "entertainment"}]
        result = _mergeCategories(existing, new)
        assert len(result) == 3
        assert [c["id"] for c in result] == ["news", "sports", "entertainment"]

    def testDeduplicatesById(self):
        existing = [{"id": "news"}, {"id": "sports"}]
        new = [{"id": "news"}, {"id": "entertainment"}]
        result = _mergeCategories(existing, new)
        assert len(result) == 3

    def testNoExisting(self):
        result = _mergeCategories(None, [{"id": "news"}])
        assert len(result) == 1
        assert result[0]["id"] == "news"


class TestFindChannel:
    async def testEmptyChannelIdReturnsNone(self, mocker):
        session = mocker.AsyncMock()
        result = await _findChannel(session, "")
        assert result is None
        session.execute.assert_not_called()


class TestMarkStreamsReachable:
    def testAddsDefaultTrueToDictStreams(self):
        result = _markStreamsReachable([{"url": "a"}, {"url": "b", "reachable": False}])
        assert result == [{"url": "a", "reachable": True}, {"url": "b", "reachable": False}]

    def testNonDictStreamsPassThrough(self):
        streams = ["legacy-entry", 42]
        assert _markStreamsReachable(streams) == ["legacy-entry", 42]

    def testNoneReturnsEmpty(self):
        assert _markStreamsReachable(None) == []

    def testOriginalDictsUntouched(self):
        stream = {"url": "a"}
        _markStreamsReachable([stream])
        assert stream == {"url": "a"}


class TestMergeUniqueUris:
    def testFromNoneDefaultsReachableTrue(self):
        result = _mergeUniqueUris(None, ["https://a.com/1"])
        assert result == [{"url": "https://a.com/1", "reachable": True}]

    def testDedupsAgainstExistingEntries(self):
        existing = [{"url": "https://a.com/1", "reachable": True}]
        result = _mergeUniqueUris(existing, ["https://a.com/1", "https://b.com/2"])
        assert [u["url"] for u in result] == ["https://a.com/1", "https://b.com/2"]
        assert result[0] is not existing[0]  # copies, never mutates input

    def testSkipsEmptyAndDuplicateNewUrls(self):
        result = _mergeUniqueUris([], ["https://a.com/1", "", "https://a.com/1"])
        assert [u["url"] for u in result] == ["https://a.com/1"]

    def testNonDictExistingEntriesDropped(self):
        result = _mergeUniqueUris(["legacy-str", {"url": "keep"}], [])
        assert result == [{"url": "keep"}]
