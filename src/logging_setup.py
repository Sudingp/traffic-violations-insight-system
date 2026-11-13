"""
Logging configuration for the live ingestion job.

Writes human-readable logs to the console and to a rotating file
(logs/ingest.log), so a scheduled run that nobody is watching still
leaves a trail you can debug from.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """Configure the root 'tvis' logger once and return it."""
    logger = logging.getLogger("tvis")
    if logger.handlers:  # already configured (e.g. called twice in one process)
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "ingest.log"),
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
