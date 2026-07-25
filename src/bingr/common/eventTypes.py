from __future__ import annotations

from dataclasses import dataclass

from bingr.common.constants import ViewModelRole


@dataclass
class ReloadChannelsDataEvent:
    doReload: bool = False
    targetRoles: tuple[str, ...] = (ViewModelRole.GRID, ViewModelRole.LIST)
