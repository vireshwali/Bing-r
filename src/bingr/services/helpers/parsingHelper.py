"""M3U playlist parser — low-level helpers for M3U8 extinf parsing.

Provides splitExtinfPayload(), parseChannelTitle(), parseTvgId(),
stripSuffix(), and parseIptvAttributesEnhanced() (the custom_tags_parser
callback for the m3u8 library). Used by enrichmentHelper and import pipeline.
"""

import logging
import re
from typing import Any

from m3u8 import protocol  # pyright: ignore[reportMissingModuleSource, reportAttributeAccessIssue]
from m3u8.parser import (
    save_segment_custom_value,  # pyright: ignore[reportMissingModuleSource, reportAttributeAccessIssue]
)

logger = logging.getLogger(__name__)


def splitExtinfPayload(payload: str) -> tuple[str, str]:
    in_quotes = False
    for i, ch in enumerate(payload):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            return payload[:i], payload[i + 1 :]
    return payload, ""


def parseChannelTitle(raw_title: str) -> dict[str, Any]:
    clean = raw_title.strip()

    res_match = re.search(r"\((\d{3,4}[pi]?)\)", clean)
    resolution = res_match.group(1) if res_match else None
    clean = re.sub(r"\((\d{3,4}[pi]?)\)", "", clean).strip()

    flags_match = re.findall(r"\[(.*?)\]", clean)
    flags = [f.strip() for f in flags_match if f.strip()]
    clean = re.sub(r"\[.*?\]", "", clean).strip()

    circle_map = {"\u24c8": "SD", "\u24ce": "YouTube"}
    for symbol, flag_name in circle_map.items():
        if symbol in clean:
            flags.append(flag_name)
            clean = clean.replace(symbol, "").strip()

    return {
        "clean_title": clean,
        "resolution": resolution,
        "flags": flags,
    }


def parseIptvAttributesEnhanced(line, lineno, data, state):
    if line.startswith("#EXTM3U"):
        match = re.search(r'x-tvg-url="([^"]*)"', line)
        if match:
            data["x_tvg_url"] = [u.strip() for u in match.group(1).split(",") if u.strip()]
        return True

    if line.startswith(protocol.extinf):
        title = ""
        payload = line.replace(protocol.extinf + ":", "", 1)
        duration_and_props, title = splitExtinfPayload(payload)

        additional_props = {}
        chunks = duration_and_props.strip().split(" ", 1)
        if len(chunks) == 2:
            duration, raw_props = chunks
            matched_props = re.finditer(r'([\w\-]+)="([^"]*)"', raw_props)
            for match in matched_props:
                additional_props[match.group(1)] = match.group(2)
        else:
            duration = duration_and_props

        parsed = parseChannelTitle(title)

        if "segment" not in state:
            state["segment"] = {}
        state["segment"]["duration"] = float(duration)
        state["segment"]["title"] = parsed["clean_title"]

        extra = {
            "raw_title": title,
            "resolution": parsed["resolution"],
            "flags": parsed["flags"],
            "extinf_props": additional_props,
        }
        save_segment_custom_value(state, "extra", extra)

        state["expect_segment"] = True
        return True


def parseTvgId(tvg_id: str) -> tuple[str, str, str]:
    channel_id = re.sub(r"@\w+", "", tvg_id).strip()
    parts = channel_id.split(".", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""
    return channel_id, prefix, suffix


def stripSuffix(tvg_id: str) -> str:
    suffixes = re.findall(r"@\w+", tvg_id)
    clean = tvg_id
    for suf in suffixes:
        clean = clean.replace(suf, "")
    return clean.strip()
