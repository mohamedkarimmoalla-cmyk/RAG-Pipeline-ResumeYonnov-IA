"""Logging helpers."""

import logging

from app.core.config import OUTPUT_DIR

logger = logging.getLogger("pdf_summarizer")
logger.setLevel(logging.INFO)

if not any(
    isinstance(existing_handler, logging.StreamHandler)
    and not isinstance(existing_handler, logging.FileHandler)
    for existing_handler in logger.handlers
):
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

log_file = OUTPUT_DIR / "logs" / "app.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
if not any(
    isinstance(existing_handler, logging.FileHandler)
    and existing_handler.baseFilename == str(log_file.resolve())
    for existing_handler in logger.handlers
):
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
