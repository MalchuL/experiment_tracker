import json
import os
from dataclasses import dataclass
from typing import Optional


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".experiment-tracker")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class SDKConfig:
    base_url: str
    api_token: str


def load_config() -> Optional[SDKConfig]:
    """Load SDK config from disk.

    Returns:
        SDKConfig if present and valid, otherwise None.
    """
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not raw.get("base_url") or not raw.get("api_token"):
        return None
    return SDKConfig(base_url=raw["base_url"], api_token=raw["api_token"])


def save_config(base_url: str, api_token: str) -> None:
    """Persist SDK config to the default config path.

    Args:
        base_url: Backend base URL.
        api_token: API token string.

    Example:
        save_config("http://127.0.0.1:8000", "my-token")
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump({"base_url": base_url, "api_token": api_token}, handle)
