import logging
import sys
from typing import Literal

_LOGGERS: dict[str, logging.Logger] = {}


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    format_str: str | None = None,
) -> None:
    """
    Configure root logging for the application.
    Defaults to stderr stream with ISO8601 timestamps.
    """
    if format_str is None:
        format_str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    logging.basicConfig(
        level=getattr(logging, level),
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger. Caches instances to avoid duplicates.
    """
    if name not in _LOGGERS:
        logger = logging.getLogger(name)
        _LOGGERS[name] = logger
    return _LOGGERS[name]
