from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtitleModel:
    name: str
    trackId: int
    langCode: str = ""
