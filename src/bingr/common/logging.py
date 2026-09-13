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

    # Explicitly route third-party loggers to your proper handlers
    # This ensures they use your format and go to both stderr + bingr.log

    third_party_loggers = [
        {"httpx": logging.ERROR},
        {"httpcore": logging.ERROR},
        {"alembic": logging.INFO},
    ]
    for logger_info in third_party_loggers:
        logger_name = next(iter(logger_info.keys()))
        level = logger_info[logger_name]
        tgt_logger = logging.getLogger(logger_name)
        tgt_logger.setLevel(level)
        tgt_logger.handlers.clear()
        tgt_logger.addHandler(stderrHandler)
        tgt_logger.addHandler(fileHandler)
        tgt_logger.propagate = False  # Stops the fallback to root stderr

    # Route print()/stdout/stderr output (mpv, ffmpeg, stray prints) through
    # the logger tree so it lands in bingr.log as well. Handlers above already
    # hold the real stream objects, so this cannot recurse.
    from .logStreamProxy import installStreamProxies

    installStreamProxies()

    bingrLogger.info("Logging initialized — stderr + %s", logFile)
