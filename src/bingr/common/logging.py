"""One-shot logging bootstrap — reads log.level from Config and applies levels.

Call setup_logging() once at startup to configure the bingr logger level
and suppress noisy alembic plugin logs.
"""

import logging

from .config import get_config
from .constants import KEYS


def setup_logging():
    cfg = get_config()
    level_name = cfg.get(KEYS.LOG_LEVEL, "INFO").upper()
    level = getattr(logging, level_name, logging.DEBUG)
    logging.root.setLevel(level)
    logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)
    logging.getLogger("bingr").setLevel(level)
