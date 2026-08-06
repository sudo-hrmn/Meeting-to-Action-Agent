"""
Logging configuration — structured, consistent logging across the app.

Why: Structured logs (with level, timestamp, module) are parseable by log
aggregators (Datadog, CloudWatch, etc.) and make debugging in production
dramatically easier than plain print() statements.
"""
import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO", app_name: str = "meeting-agent") -> None:
    """
    Configure structured logging for the application.

    Uses a consistent format: [LEVEL] timestamp | module | message
    This makes grepping and filtering logs straightforward.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger configuration
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(app_name)
    logger.info(f"Logging initialised at level: {log_level}")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a named logger for a module.

    Usage:
        logger = get_logger(__name__)
        logger.info("Meeting uploaded", extra={"meeting_id": id})
    """
    return logging.getLogger(name or "meeting-agent")
