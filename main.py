from __future__ import annotations

import logging
import os

from learning_tool.cli import main as cli_main


def configure_logging() -> None:
    """Configure basic logging for the application.  # NF7"""
    log_level_name = os.getenv("LEARNING_TOOL_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(levelname)s:%(name)s:%(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    cli_main()
