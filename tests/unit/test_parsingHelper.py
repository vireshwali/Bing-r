from typing import Any

import pytest

from bingr.services.helpers.parsingHelper import (
    parseChannelTitle,
    parseIptvAttributesEnhanced,
    parseTvgId,
    splitExtinfPayload,
    stripSuffix,
)


@pytest.mark.parametrize(
    ("payload", "expectedProps", "expectedTitle"),
    [
        pytest.param(
            '100.0 tvg-id="abc" tvg-name="Foo",Channel Name',
            '100.0 tvg-id="abc" tvg-name="Foo"',
            "Channel Name",
            id="split_extinf_payload_basic",
        ),
        pytest.param(
            '100.0 tvg-name="Bar, Baz",Channel',
            '100.0 tvg-name="Bar, Baz"',
            "Channel",
            id="split_extinf_payload_quoted_comma",
        ),
        pytest.param("100.0", "100.0", "", id="split_extinf_payload_no_comma"),
    ],
)
def testSplitExtinfPayload(payload, expectedProps, expectedTitle):
    props, title = splitExtinfPayload(payload)
    assert props == expectedProps
    assert title == expectedTitle


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(
            "BHT 1", {"clean_title": "BHT 1", "resolution": None, "flags": []}, id="parse_channel_title_clean"
        ),
        pytest.param(
            "BHT 1 (720p)",
            {"clean_title": "BHT 1", "resolution": "720p", "flags": []},
            id="parse_channel_title_res_720p",
        ),
        pytest.param(
            "BHT 1 (576i)",
            {"clean_title": "BHT 1", "resolution": "576i", "flags": []},
            id="parse_channel_title_res_576i",
        ),
        pytest.param(
            "BHT 1 (1080)",
            {"clean_title": "BHT 1", "resolution": "1080", "flags": []},
            id="parse_channel_title_res_1080",
        ),
        pytest.param(
            "BHT 1 [Not 24/7]",
            {"clean_title": "BHT 1", "resolution": None, "flags": ["Not 24/7"]},
            id="parse_channel_title_flags_single",
        ),
        pytest.param(
            "BHT 1 [HD] [Not 24/7]",
            {"clean_title": "BHT 1", "resolution": None, "flags": ["HD", "Not 24/7"]},
            id="parse_channel_title_flags_multi",
        ),
        pytest.param(
            "BHT 1 \u24c8",
            {"clean_title": "BHT 1", "resolution": None, "flags": ["SD"]},
            id="parse_channel_title_unicode_sd",
        ),
        pytest.param(
            "BHT 1 \u24ce",
            {"clean_title": "BHT 1", "resolution": None, "flags": ["YouTube"]},
            id="parse_channel_title_unicode_youtube",
        ),
        pytest.param(
            "BHT 1 (1080p) [HD] \u24c8",
            {"clean_title": "BHT 1", "resolution": "1080p", "flags": ["HD", "SD"]},
            id="parse_channel_title_all",
        ),
        pytest.param("", {"clean_title": "", "resolution": None, "flags": []}, id="parse_channel_title_empty"),
        pytest.param(
            "[Some Flag]",
            {"clean_title": "", "resolution": None, "flags": ["Some Flag"]},
            id="parse_channel_title_only_brackets",
        ),
    ],
)
def testParseChannelTitle(raw, expected):
    assert parseChannelTitle(raw) == expected


def testParseIptvAttributesEnhancedExtm3uWithXTvgUrl():
    data = {}
    result = parseIptvAttributesEnhanced(
        '#EXTM3U x-tvg-url="https://epg.example.com,https://epg2.example.com"',
        1,
        data,
        {},
    )
    assert result is True
    assert data["x_tvg_url"] == ["https://epg.example.com", "https://epg2.example.com"]


def testParseIptvAttributesEnhancedExtm3uWithoutXTvgUrl():
    data = {}
    result = parseIptvAttributesEnhanced("#EXTM3U", 1, data, {})
    assert result is True
    assert "x_tvg_url" not in data


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param(
            '#EXTINF:100.0 tvg-id="BHT1.ba" tvg-name="BHT 1" group-title="BA",BHT 1 (1080p)',
            {
                "duration": 100.0,
                "title": "BHT 1",
                "extra": {
                    "raw_title": "BHT 1 (1080p)",
                    "resolution": "1080p",
                    "extinf_props": {
                        "tvg-id": "BHT1.ba",
                        "tvg-name": "BHT 1",
                        "group-title": "BA",
                    },
                },
            },
            id="extinf_all_attributes",
        ),
        pytest.param(
            "#EXTINF:-1,Live Stream",
            {"duration": -1.0, "title": "Live Stream", "extra": None},
            id="extinf_minimal",
        ),
    ],
)
def testParseIptvAttributesEnhancedExtinf(line, expected):
    state: dict[str, Any] = {}
    result = parseIptvAttributesEnhanced(line, 2, {}, state)
    assert result is True
    assert state["segment"]["duration"] == pytest.approx(expected["duration"])
    assert state["segment"]["title"] == expected["title"]
    assert state["expect_segment"] is True
    if expected["extra"] is not None:
        extra = state["segment"]["custom_parser_values"]["extra"]
        for k, v in expected["extra"].items():
            if isinstance(v, dict):
                for subK, subV in v.items():
                    assert extra[k][subK] == subV
            else:
                assert extra[k] == v


def testParseIptvAttributesEnhancedOtherLine():
    result = parseIptvAttributesEnhanced(
        "#EXTVLCOPT:http-user-agent=Foo",
        4,
        {},
        {},
    )
    assert result is None


@pytest.mark.parametrize(
    ("tvgId", "expected"),
    [
        pytest.param("BHT1.ba", ("BHT1.ba", "BHT1", "ba"), id="parse_tvg_id_prefix_suffix"),
        pytest.param("BHT1", ("BHT1", "BHT1", ""), id="parse_tvg_id_prefix_only"),
        pytest.param("BHT1.ba@HD", ("BHT1.ba", "BHT1", "ba"), id="parse_tvg_id_with_at_suffix"),
        pytest.param("", ("", "", ""), id="parse_tvg_id_empty"),
    ],
)
def testParseTvgId(tvgId, expected):
    assert parseTvgId(tvgId) == expected


@pytest.mark.parametrize(
    ("tvgId", "expected"),
    [
        pytest.param("BHT1.ba@HD", "BHT1.ba", id="strip_suffix_hd"),
        pytest.param("BHT1.ba@SD", "BHT1.ba", id="strip_suffix_sd"),
        pytest.param("BHT1.ba", "BHT1.ba", id="strip_suffix_none"),
        pytest.param("Foo@HD@extra", "Foo", id="strip_suffix_multiple"),
        pytest.param("", "", id="strip_suffix_empty"),
    ],
)
def testStripSuffix(tvgId, expected):
    assert stripSuffix(tvgId) == expected
