"""App configuration — singleton Config, dotenv loading, and type inference.

Config loads .env files (shipped + user + env vars) and provides typed accessors
(get, get_int, get_bool). _infer() converts raw strings to bool/int/float/Path.
get_config() returns the lazily-initialised singleton Config.
"""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key

logger = logging.getLogger(__name__)


def _infer(raw: str) -> Any:
    lr = raw.lower()
    if lr in ("true", "false"):
        return lr == "true"
    if raw.startswith("~") or raw.startswith("/"):
        return Path(raw).expanduser()
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


DOTENV_LOCATIONS = [
    Path.home() / ".config" / "bingr" / ".env",
    Path.home() / ".bingr" / ".env",
]

SHIPPED_DOTENV = Path(__file__).resolve().parent.parent.parent.parent / "config" / ".env"


class Config:
    __slots__ = ("_dotenv_paths", "_store")

    def __init__(self, dotenv_path: str | Path | None = None):
        self._store: dict[str, str] = {}
        self._dotenv_paths: list[Path] = []

        self._load_one(SHIPPED_DOTENV)

        for p in DOTENV_LOCATIONS:
            if p.exists():
                self._load_one(p)

        if dotenv_path:
            p = Path(dotenv_path).expanduser()
            if p.exists():
                self._load_one(p)

        for key, val in os.environ.items():
            if "." in key and val:
                self._store[key] = val

    def _load_one(self, path: Path) -> None:
        values = dotenv_values(str(path))
        for key, val in values.items():
            if val is not None:
                self._store[key] = val
        self._dotenv_paths.append(path)

    def get(self, key: str, default: Any = None) -> Any:
        raw = self._store.get(key, "")
        if not raw:
            return default
        return _infer(raw)

    def get_int(self, key: str, default: int = 0) -> int:
        raw = self._store.get(key, "")
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "Config key %r has non-integer value %r — returning default %d",
                key,
                raw,
                default,
                exc_info=True,
            )
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        raw = self._store.get(key, "").lower()
        if raw == "true":
            return True
        if raw == "false":
            return False
        if raw:
            logger.warning(
                "Config key %r has non-boolean value %r — returning default %s",
                key,
                raw,
                default,
            )
        return default

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        self._store[key] = str(value)
        if persist and self._dotenv_paths:
            set_key(str(self._dotenv_paths[-1]), key, str(value))


_config_instance: Config | None = None


def get_config(dotenv_path: str | Path | None = None) -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(dotenv_path)
    return _config_instance
