from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourcesProcessingStatusModel:
    name: str
    status: str = "Pending"
