import logging
import os
import sys


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.handlers.clear()
    logger.addHandler(handler)
    os.environ["LOGLEVEL"] = level.upper()
    return logger


def redact_text(text: str) -> str:
    lvl = os.getenv("LOGLEVEL", "INFO").upper()
    if lvl in {"INFO", "WARN", "WARNING"}:
        return "[REDACTED]"
    return text

