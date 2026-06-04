import logging
import sys
import os

from src.config.loader import load_config


def setup_logging():
    """
    Configure global logging for all services
    """

    # Get the app environment
    try:
        config = load_config()
        app_env = config.get("app", {}).get("env", "development")
    except Exception as e:
        app_env = "development"

    # Set the log level based on the environment
    log_level = logging.DEBUG if app_env == "development" else logging.INFO

    # Set the root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        # Get the log format
        log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        formatter = logging.Formatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")

        # Redirect logs to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Add handlers to the root logger
        root_logger.addHandler(console_handler)