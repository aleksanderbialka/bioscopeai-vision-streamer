from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from loguru import Logger
import sys

from loguru import logger

from bioscopeai_vision_streamer.app.core import settings


def setup_logger() -> Logger:
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        level=settings.app.LOG_LEVEL.upper(),
    )
    logger.add(
        settings.app.LOG_FILE_PATH,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level=settings.app.LOG_FILE_LEVEL.upper(),
    )
    return logger
