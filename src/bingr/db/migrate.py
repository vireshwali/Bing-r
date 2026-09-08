"""Alembic migration runner — applies DB schema migrations via Alembic.

runMigrations() locates alembic.ini (shipped or caller-provided), sets the
sqlalchemy.url, and runs all pending migrations. Called at app startup and
in integration test fixtures.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

_ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"
_ALEMBIC_DIR = Path(__file__).resolve().parent / "alembic"


def runMigrations(dbPath: str | Path, alembicIniPath: str | Path | None = None):
    ini = alembicIniPath or _ALEMBIC_INI
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{dbPath}")
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    command.upgrade(cfg, "head")
