"""
Structured logging setup for the bot.
Creates file + console handlers with rich formatting.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import config


def setup_logging() -> logging.Logger:
    """Configure and return the root logger."""
    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    # ── Formatters ────────────────────────────────────────────────────────────
    detailed_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Root logger ───────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(log_level)

    # ── Console handler ───────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_fmt)
    root.addHandler(console_handler)

    # ── Rotating file handler ─────────────────────────────────────────────────
    log_file = log_dir / config.LOG_FILE
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_fmt)
    root.addHandler(file_handler)

    # ── Silence noisy libraries ───────────────────────────────────────────────
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    return logging.getLogger("bot")


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger."""
    return logging.getLogger(f"bot.{name}")
