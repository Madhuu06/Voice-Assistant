"""
logger.py — Structured logging with timestamps and colored console output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Colored log output for console."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """
    Set up structured logging with file and colored console handlers.

    Returns:
        Logger instance named 'maya'.
    """
    logger_name = "maya"

    # Avoid duplicate handlers on repeated calls
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # ── Log directory ────────────────────────────────────────
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # ── File handler (ISO timestamps, detailed) ──────────────
    file_handler = logging.FileHandler(
        log_dir / "maya.log", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))

    # ── Console handler (colored, concise) ───────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    # Force UTF-8 encoding on Windows
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
    console_handler.setFormatter(ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
