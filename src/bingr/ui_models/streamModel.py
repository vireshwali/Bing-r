from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StreamModel:
    name: str
    url: str
    langCode: str = ""
