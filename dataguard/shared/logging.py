"""Centralised logging configuration and logger factory.

Every module in DataGuard should obtain its logger via get_logger(__name__)
instead of calling logging.getLogger() directly. This ensures consistent
formatting and that the log level is always sourced from application config.

Usage
-----
    from dataguard.shared.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Processing started", extra={"source": "data.csv"})

Design notes
------------
- configure_logging() is called once at application startup (CLI entry point).
- get_logger() is safe to call before configure_logging() — it returns a
  logger that will pick up handlers once the root logger is configured.
- No third-party logging libraries (e.g. loguru) are used to keep
  the dependency surface minimal.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
)
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

_configured: bool = False


def configure_logging(level: str = "INFO") -> None:
    """Set up the root logger with a stdout StreamHandler.

    This function is idempotent — calling it multiple times has no effect
    after the first successful configuration.

    Args:
        level: Logging level string (e.g. 'DEBUG', 'INFO'). Case-insensitive.
    """
    global _configured  # noqa: PLW0603 — intentional module-level flag
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    )

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.addHandler(handler)

    # Silence noisy third-party loggers that DataGuard does not own.
    for noisy in ("urllib3", "asyncio", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-specific logger.

    The logger inherits its level and handlers from the root logger, which
    must be configured via configure_logging() at application startup.

    Args:
        name: Logger name, conventionally __name__ of the calling module.

    Returns:
        logging.Logger: A standard library logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Rule loaded", extra={"rule_id": "rule_001"})
    """
    return logging.getLogger(name)
