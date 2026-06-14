from functools import lru_cache
from pathlib import Path

from src.config.loader import load_config


@lru_cache(maxsize=1)
def load_test_config():
    config_path = Path(__file__).parent / "test_config.yml"
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

    config = load_config(config_path, env_path)
    return config


