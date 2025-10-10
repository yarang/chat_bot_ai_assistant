import os
import logging


def setup_logging(config: dict):
    """Set up logging to file and console."""
    log_level_str = config.get("app", {}).get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplication
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # File handler
    file_handler = logging.FileHandler("logs/app.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
