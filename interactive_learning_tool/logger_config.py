from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import CONFIG


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger for the given module.

    Requirements:
        - FR-12: Logging & diagnostics
        - NFR-10: Structured logging
        - SEC-4: No secrets in logs
    """
    log_dir: Path = CONFIG.log_dir
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=512 * 1024, backupCount=3
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
