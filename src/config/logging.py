import logging
import sys
import os
from datetime import datetime
from pathlib import Path

from src.config.loader import load_config


def setup_logging():
    """
    Configure global logging for all services
    """

    # 1. Get the app environment
    try:
        config = load_config()
        app_env = config.get("app", {}).get("env", "development")
    except Exception as e:
        app_env = "development"

    log_level = logging.INFO if app_env == "development" else logging.INFO

    # 2. Set output dir
    ROOT_DIR = Path(__file__).parent.parent.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_dir = ROOT_DIR / "outputs" / timestamp / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 3. Set up log format
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)


    # Set the root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 4. For root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        # Add handlers to the root logger
        root_logger.addHandler(console_handler)
        # Normal FileHandler for all loggers
        sys_file_handler = logging.FileHandler(str(logs_dir / "system.log"), mode="a", encoding="utf-8")
        sys_file_handler.setFormatter(formatter)
        root_logger.addHandler(sys_file_handler)

    # 5. For LLM
    llm_logger = logging.getLogger("llm_io")
    llm_logger.setLevel(log_level)
    llm_logger.propagate = True

    if not llm_logger.handlers:
        llm_file_handler = logging.FileHandler(str(logs_dir / "llm.log"), mode="a", encoding="utf-8")
        llm_file_handler.setFormatter(formatter)
        llm_logger.addHandler(llm_file_handler)

    # 6. For Regex log
    regex_logger = logging.getLogger("regex_output")
    regex_logger.setLevel(log_level)
    regex_logger.propagate = True

    if not regex_logger.handlers:
        regex_file_handler = logging.FileHandler(str(logs_dir / "regex.log"), mode="a", encoding="utf-8")
        regex_file_handler.setFormatter(formatter)
        regex_logger.addHandler(regex_file_handler)