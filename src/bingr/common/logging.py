"""One-shot logging bootstrap — reads log.level from Config and applies levels.

Call setupLogging() once at startup to configure the bingr logger level,
suppress noisy alembic plugin logs, and set up persistent file logging
for crash reports.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import getConfig
from .constants import KEYS

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_LOG_BACKUP_COUNT = 3


def setupLogging():
    cfg = getConfig()
    levelName = cfg.get(KEYS.LOG_LEVEL, "INFO").upper()
    level = getattr(logging, levelName, logging.INFO)
    logging.root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)

    # stderr handler (always — Flatpak captures via flatpak run --log-session)
    stderrHandler = logging.StreamHandler(sys.stderr)
    stderrHandler.setFormatter(formatter)

    bingrLogger = logging.getLogger("bingr")
    bingrLogger.setLevel(level)
    bingrLogger.handlers.clear()
    bingrLogger.addHandler(stderrHandler)

    # file handler (persistent logs for crash reports / "send error info")
    logDir = cfg.logDir()
    logDir.mkdir(parents=True, exist_ok=True)
    logFile = logDir / "bingr.log"
    fileHandler = RotatingFileHandler(
        str(logFile),
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fileHandler.setFormatter(formatter)
    bingrLogger.addHandler(fileHandler)

    bingrLogger.propagate = False

    logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)

    bingrLogger.info("Logging initialized — stderr + %s", logFile)
