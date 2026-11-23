"""Structured logging configuration for PCB Insight."""

import logging
import sys
from typing import Optional

LOGGER_NAME = "pcb_insight"


def setup_logger(
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Configures and returns the central logger for PCB Insight."""
    logger = logging.getLogger(LOGGER_NAME)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s.%(module)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)
        except OSError as e:
            logger.warning(f"Failed to attach log file '{log_file}': {e}")

    return logger


def get_logger() -> logging.Logger:
    """Returns the logger instance, initializing with defaults if needed."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        return setup_logger()
    return logger
