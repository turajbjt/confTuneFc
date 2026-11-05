"""
Logging subsystem for ConfTune FC.
Provides rotating disk logging, console output, and in-memory listeners for the GUI log tab.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Callable, List

LOGGER_NAME = "conftune"
_LOG_LISTENERS: List[Callable[[str, int], None]] = []


class SignalHandler(logging.Handler):
    """Custom logging handler that dispatches log records to UI subscribers."""

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        for listener in _LOG_LISTENERS:
            try:
                listener(msg, record.levelno)
            except Exception:
                pass


def add_log_listener(callback: Callable[[str, int], None]) -> None:
    """Register a UI callback to receive log records."""
    if callback not in _LOG_LISTENERS:
        _LOG_LISTENERS.append(callback)


def remove_log_listener(callback: Callable[[str, int], None]) -> None:
    """Unregister a UI callback."""
    if callback in _LOG_LISTENERS:
        _LOG_LISTENERS.remove(callback)


def get_log_dir() -> str:
    """Determine best log directory depending on user privileges."""
    if os.geteuid() == 0:
        log_dir = "/var/log/conftune"
    else:
        log_dir = os.path.expanduser("~/.local/share/conftune/logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = "/tmp/conftune/logs"
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass
    return log_dir


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Initialize root application logger."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_dir = get_log_dir()
        log_file = os.path.join(log_dir, "conftune.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not configure file logger: {e}\n")

    # GUI Signal Handler
    sig_handler = SignalHandler()
    sig_handler.setFormatter(formatter)
    logger.addHandler(sig_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get active application logger or initialize one."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        return setup_logger()
    return logger
