"""iptv-org enrichment engine — channel lookup, feed matching, and data expansion.

Provides lookupChannel(), lookupFeeds(), lookupStreams(), feed matching
via matchFeed(), and full segment enrichment via enrichSegment() which
resolves broadcast_area, categories, languages, and picks the best feed/stream
match.  API data is sourced from the app-wide FileDataCache singleton.
"""

import logging
import re
from typing import Any

from bingr.common.cache import getFileCache
from bingr.services.helpers.parsingHelper import parseChannelTitle, stripSuffix

logger = logging.getLogger(__name__)

_countryCodeAliases: dict[str, str] = {
    "UK": "GB",
}


def _normalizeCountryCode(code: str) -> str:
    """Return a canonical ISO 3166-1 alpha-2 code.

    iptv-org uses non-standard codes for some countries (e.g. ``UK`` for the
    United Kingdom); map those to the canonical code used by external services
    such as flagcdn.com.
    """
    upper = code.upper()
    return _countryCodeAliases.get(upper, upper)


def ensureAllCaches():
    getFileCache().ensureAll()


def _expandCountry(code: str) -> dict[str, Any] | None:
    if not code:
        return None
    data = getFileCache().load("countries")
    codeUpper = _normalizeCountryCode(code)
    for c in data:
        if _normalizeCountryCode(c.get("code", "")).upper() == codeUpper:
            return {"code": codeUpper, "name": c.get("name", ""), "flag": c.get("flag", "")}
    logger.warning("country miss: %s not found", code)
    return None


def _expandSubdivision(code: str) -> dict[str, Any] | None:
    if not code:
        return None
    data = getFileCache().load("subdivisions")
    for s in data:
        if s.get("code", "") == code:
            return {"code": s["code"], "name": s.get("name", ""), "country": s.get("country", "")}
    logger.warning("subdivision miss: %s not found", code)
    return None


def _expandRegion(code: str) -> dict[str, Any] | None:
    if not code:
        return None
    data = getFileCache().load("regions")
    codeUpper = code.upper()
    for r in data:
        if r.get("code", "").upper() == codeUpper:
            return {"code": r["code"], "name": r.get("name", "")}
    logger.warning("region miss: %s not found", code)
    return None


def _expandCity(code: str) -> dict[str, Any] | None:
    if not code:
        return None
    data = getFileCache().load("cities")
    codeLower = code.lower()
    for c in data:
        if c.get("code", "").lower() == codeLower:
            return {"code": c["code"], "name": c.get("name", ""), "country": c.get("country", "")}
    logger.warning("city miss: %s not found", code)
    return None


def _expandBroadcastArea(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    if raw.startswith("ct/"):
        return _expandCity(raw[3:])
    elif raw.startswith("c/"):
        return _expandCountry(raw[2:])
    elif raw.startswith("s/"):
        return _expandSubdivision(raw[2:])
    elif raw.startswith("r/"):
        return _expandRegion(raw[2:])
    else:
        logger.warning("unknown broadcast_area prefix: %s", raw)
        return None


def _expandCategories(ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    data = getFileCache().load("categories")
    idSet = set(ids)
    found = [
        {"id": c.get("id", ""), "name": c.get("name", ""), "description": c.get("description", "")}
        for c in data
        if c.get("id") in idSet
    ]
    missing = set(ids) - {c["id"] for c in found}
    if missing:
        logger.warning("categories miss: %s not found in API", missing)
    return found


def _expandLanguages(codes: list[str]) -> list[dict[str, Any]]:
    if not codes:
        return []
    data = getFileCache().load("languages")
    codeSet = set(codes)
    found = [{"code": c.get("code", ""), "name": c.get("name", "")} for c in data if c.get("code") in codeSet]
    missing = set(codes) - {c["code"] for c in found}
    if missing:
        logger.warning("languages miss: %s not found in API", missing)
    return found


def isCountryName(value: str) -> bool:
    if not value:
        return False
    data = getFileCache().load("countries")
    lower = value.lower().strip()
    return any(
        lower == c.get("name", "").lower()
        or lower == c.get("code", "").lower()
        for c in data
    )


def lookupChannel(tvg_id: str) -> dict[str, Any] | None:
    if not tvg_id:
        return None
    searchId = stripSuffix(tvg_id)
    channels = getFileCache().load("channels")
    for ch in channels:
        if ch.get("id") == searchId:
            return ch
    return None


def lookupFeeds(channel_id: str) -> list[dict[str, Any]]:
    if not channel_id:
        return []
    data = getFileCache().load("feeds")
    feeds = [f for f in data if f.get("channel") == channel_id]
    return feeds


def lookupStreams(channel_id: str, feed_id: str | None) -> list[dict[str, Any]]:
    if not feed_id or not channel_id:
        return []
    data = getFileCache().load("streams")
    streams = [s for s in data if s.get("feed") == feed_id and s.get("channel") == channel_id]
    return streams


_SUFFIX_FORMAT_MAP: dict[str, str | None] = {
    "HD": None,
    "1080I": "1080i",
    "1080P": "1080p",
    "720P": "720p",
    "SD": None,
    "576I": "576i",
    "480I": "480i",
}


def _parseSuffix(tvg_id: str) -> str:
    match = re.search(r"@(\w+)", tvg_id)
    suffix = match.group(1) if match else ""
    return suffix


def _suffixToFormat(suffix: str) -> str | None:
    if not suffix:
        return None
    upper = suffix.upper()
    result = _SUFFIX_FORMAT_MAP.get(upper)
    return result


def _suffixToRegion(suffix: str) -> str | None:
    if not suffix:
        return None
    upper = suffix.upper()
    if upper == "MEXICO":
        return "c/MX"
    if upper == "PANREGIONAL":
        return "r/"
    return None


def _suffixMatchesFeedName(suffix: str, feedName: str) -> bool:
    if not suffix or not feedName:
        return False
    nameClean = feedName.lower().replace(" ", "").replace("-", "")
    sufClean = suffix.lower()
    result = sufClean in nameClean
    return result


def _scoreFeed(feed: dict[str, Any], suffix: str, suffixFmt: str | None, suffixRegion: str | None) -> int:
    score = 0
    fmt = feed.get("format")
    name = feed.get("name", "")
    areas = feed.get("broadcast_area", [])

    if suffixFmt is not None and fmt == suffixFmt:
        score += 3
    if suffixFmt is None and fmt == "SD":
        score += 1
    if suffixRegion:
        for area in areas:
            if area.startswith(suffixRegion):
                score += 3
    if _suffixMatchesFeedName(suffix, name):
        score += 2
    if feed.get("is_main"):
        score += 1
    return score


def _scoreCandidates(feeds: list[dict[str, Any]], suffix: str, suffixFmt: str | None, suffixRegion: str | None) -> list[tuple[dict[str, Any], int]]:
    scored = [(_scoreFeed(f, suffix, suffixFmt, suffixRegion), f) for f in feeds]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(f, s) for s, f in scored]


def _tryPhase2(feeds, suffix, suffixFmt, suffixRegion, bestScore):
    if not suffix:
        return None
    m = re.match(r"Plus(\d+)", suffix, re.IGNORECASE)
    if m:
        altSuffix = "+" + m.group(1)
        logger.info("feed match: Phase 2 trying %s -> %s", suffix, altSuffix)
        altFmt = _suffixToFormat(altSuffix)
        altRegion = _suffixToRegion(altSuffix)
        altScored = _scoreCandidates(feeds, altSuffix, altFmt, altRegion)
        if altScored and altScored[0][1] > bestScore:
            logger.info("feed match: Phase 2 matched feed %s (score=%d)", altScored[0][0].get("id"), altScored[0][1])
            return altScored[0][0]
    return None


def matchFeed(tvg_id: str, feeds: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not feeds:
        logger.warning("matchFeed: no feeds to match against")
        return None

    suffix = _parseSuffix(tvg_id)
    if not suffix:
        pick = next((f for f in feeds if f.get("is_main")), feeds[0])
        return pick

    suffixFmt = _suffixToFormat(suffix)
    suffixRegion = _suffixToRegion(suffix)
    candidates = _scoreCandidates(feeds, suffix, suffixFmt, suffixRegion)

    if not candidates or candidates[0][1] <= 1:
        phase2 = _tryPhase2(feeds, suffix, suffixFmt, suffixRegion, candidates[0][1] if candidates else 0)
        if phase2:
            return phase2

    if candidates:
        return candidates[0][0]

    logger.warning(
        "feed match: suffix=%r scored 0 on all %d feeds, falling back to is_main/first",
        suffix, len(feeds)
    )
    return next((f for f in feeds if f.get("is_main")), feeds[0])


def _pickMatchingStream(m3u_url: str, streams: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not m3u_url or not streams:
        return None
    maxScore = 0
    best = None
    for s in streams:
        score = 0
        sUrl = s.get("url", "")
        if sUrl and sUrl == m3u_url:
            score += 3
        elif sUrl and m3u_url and sUrl.split("?")[0] == m3u_url.split("?")[0]:
            score += 1
        if score > maxScore:
            maxScore = score
            best = s
    if not best:
        logger.warning("pick_matching_stream: no match among %d streams", len(streams))
    return best


def enrichSegment(segment) -> dict[str, Any]:
    extra = getattr(segment, "custom_parser_values", {}).get("extra", {})
    raw_title = extra.get("raw_title", segment.title)
    parsed = parseChannelTitle(raw_title)
    extinf_props = extra.get("extinf_props", {})
    tvg_id = extinf_props.get("tvg-id") or extinf_props.get("tvg_id", "")

    tvg_name = extinf_props.get("tvg-name", "")

    result = {
        "tvg_id": tvg_id,
        "group_title": extinf_props.get("group-title", ""),
        "uri": segment.uri,
        "title": raw_title,
        "clean_title": parsed["clean_title"],
        "tvg_name": tvg_name,
        "display_name": tvg_name or parsed["clean_title"],
        "raw_title": raw_title,
        "resolution": extra.get("resolution", parsed.get("resolution")),
        "flags": extra.get("flags", parsed.get("flags", [])),
        "duration": segment.duration,
        "tvg_logo": extinf_props.get("tvg-logo", ""),
    }

    channelCountry = None
    if extinf_props.get("tvg-country"):
        channelCountry = _expandCountry(extinf_props["tvg-country"])
    result["country"] = channelCountry

    if not tvg_id:
        logger.warning("enrich: no tvg_id for segment title=%r, uri=%s", raw_title, segment.uri[:80] if segment.uri else "N/A")
        return result

    ch = lookupChannel(tvg_id)
    if not ch:
        logger.warning("enrich: channel not found for tvg_id=%r (channel_id=%r)", tvg_id, stripSuffix(tvg_id))
        return result


    chCats = _expandCategories(ch.get("categories", []))
    iptvCountry = _expandCountry(ch.get("country", "")) if ch.get("country") else None

    result["display_name"] = tvg_name or ch.get("name", "") or parsed["clean_title"]
    result["country"] = channelCountry or iptvCountry

    result["channel"] = {
        "id": ch.get("id", ""),
        "name": ch.get("name", ""),
        "alt_names": ch.get("alt_names", []),
        "country": iptvCountry,
        "categories": chCats,
        "website": ch.get("website"),
    }

    channel_id = stripSuffix(tvg_id)
    feeds = lookupFeeds(channel_id)
    if not feeds:
        logger.warning("enrich: no feeds for channel %s", channel_id)
        return result

    matched = matchFeed(tvg_id, feeds)
    matchedId = matched.get("id") if matched else None

    feedsOut = []
    for f in feeds:
        feed_id = f.get("id", "")
        streams = lookupStreams(channel_id, feed_id)

        baExpanded = [_expandBroadcastArea(a) for a in f.get("broadcast_area", [])]
        baExpanded = [b for b in baExpanded if b is not None]
        flExpanded = _expandLanguages(f.get("languages", []))

        feedEntry = {
            "id": f.get("id"),
            "name": f.get("name"),
            "format": f.get("format"),
            "is_main": f.get("is_main", False),
            "broadcast_area": baExpanded,
            "languages": flExpanded,
            "timezones": f.get("timezones", []),
            "streams": [
                {
                    "url": s.get("url"),
                    "quality": s.get("quality"),
                    "label": s.get("label"),
                }
                for s in streams
            ]
            if streams
            else [],
        }
        feedsOut.append(feedEntry)

    result["feeds"] = feedsOut
    result["matched_feed_id"] = matchedId

    if matched:
        matchedStreams = lookupStreams(channel_id, matchedId)
        if not _pickMatchingStream(segment.uri, matchedStreams):
            logger.warning("enrich: M3U URI has no matching API stream among %d candidates", len(matchedStreams))

    return result


def resolveChannelId(source_name: str, enriched: dict[str, Any]) -> str:
    raw = enriched.get("tvg_id", "")
    if raw.strip():
        return stripSuffix(raw.strip())
    slug = re.sub(r"[^a-z0-9_]", "", enriched.get("title", "unknown").lower().replace(" ", "_"))[:50]
    safeSrc = re.sub(r"[^a-z0-9_]", "", source_name.lower().replace(" ", "_"))[:30]
    return f"not_found_{safeSrc}_{slug}"
