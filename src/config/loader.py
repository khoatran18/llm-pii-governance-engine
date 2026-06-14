import os
import re
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_config(config_path = None, env_path = None) -> dict:
    # Get path
    if not config_path:
        config_path = Path(__file__).parent / "app_config.yml"
    if not env_path:
        env_path = Path(__file__).parent.parent.parent / ".env"

    # Load .env
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)

    # Load config
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Compile and substitute environment variables
    pattern = re.compile(r"\$\{(\w+)\}")
    content = pattern.sub(lambda m: os.getenv(m.group(1), m.group(0)), content) # group(0) contains ${}, group(1) contains the variable name

    # Get dict
    return yaml.load(content, Loader=yaml.SafeLoader)

if __name__ == "__main__":
    print(load_config())
