import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from experiment_tracker_sdk.error import ExpTrackerConfigError


CONFIG_DIR = Path.home() / ".experiment-tracker"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class SDKConfig:
    base_url: str
    api_token: str


def load_config() -> SDKConfig:
    """Load SDK config from disk.

    Returns:
        SDKConfig if present and valid, otherwise raises ExpTrackerConfigError.
    """
    if not CONFIG_PATH.exists():
        raise ExpTrackerConfigError(f"Config file not found at path: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not raw.get("base_url"):
        raise ExpTrackerConfigError(f"Config file is missing base_url: {CONFIG_PATH}")
    if not raw.get("api_token"):
        raise ExpTrackerConfigError(f"Config file is missing api_token: {CONFIG_PATH}")
    return SDKConfig(base_url=raw["base_url"], api_token=raw["api_token"])


def save_config(base_url: str, api_token: str) -> None:
    """Persist SDK config to the default config path.

    Args:
        base_url: Backend base URL.
        api_token: API token string.

    Example:
        save_config("http://127.0.0.1:8000", "my-token")
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump({"base_url": base_url, "api_token": api_token}, handle)
