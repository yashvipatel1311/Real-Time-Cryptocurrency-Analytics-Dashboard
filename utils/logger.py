"""
logger.py — Centralized Logging Module
======================================

Sets up structured logging to both the console and file-based logs.
Maintains rolling log files to prevent disk space exhaustion.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Setup logs directory relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Define formatting string
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Get a pre-configured logger instance that prints to both stdout and a
    rotating log file on disk.

    Parameters
    ----------
    name : str
        The name of the logger (typically `__name__` of the calling module).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # If the logger is already configured, return it to avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Rotating)
    # 5 MB max size, keeping up to 5 backups
    file_handler = RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent double-logging to root logger if configured
    logger.propagate = False

    return logger


if __name__ == "__main__":
    test_logger = get_logger("logger_test")
    test_logger.info("Centralized logging utility is configured correctly.")
    test_logger.warning("This is a test warning message.")
    print("Logs have been saved to logs/app.log")
