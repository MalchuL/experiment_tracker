import json
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from experiment_tracker_sdk.error import ExpTrackerConfigError


CONFIG_DIR = Path.home() / ".experiment-tracker"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class SDKConfig:
    base_url: str
    api_token: str
    api_prefix: str = "/api"


def normalize_api_prefix(api_prefix: str | None) -> str:
    if api_prefix is None:
        return "/api"
    trimmed = api_prefix.strip()
    if trimmed == "":
        return ""
    return f"/{trimmed.strip('/')}"


def compose_base_url(base_url: str, api_prefix: str | None) -> str:
    normalized_prefix = normalize_api_prefix(api_prefix)
    split = urlsplit(base_url.strip())
    path = split.path.rstrip("/")
    if normalized_prefix:
        if path.endswith(normalized_prefix):
            composed_path = path
        else:
            composed_path = f"{path}{normalized_prefix}" if path else normalized_prefix
    else:
        composed_path = path
    return urlunsplit((split.scheme, split.netloc, composed_path, split.query, split.fragment))


def load_config() -> SDKConfig:
    """Load SDK config from disk.

    Returns:
        SDKConfig if present and valid, otherwise raises ExpTrackerConfigError.
    """
    config_path = Path(CONFIG_PATH)

    if not config_path.exists():
        raise ExpTrackerConfigError(f"Config file not found at path: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not raw.get("base_url"):
        raise ExpTrackerConfigError(f"Config file is missing base_url: {config_path}")
    if not raw.get("api_token"):
        raise ExpTrackerConfigError(f"Config file is missing api_token: {config_path}")
    return SDKConfig(
        base_url=raw["base_url"],
        api_token=raw["api_token"],
        api_prefix=normalize_api_prefix(raw.get("api_prefix", "/api")),
    )


def save_config(base_url: str, api_token: str, api_prefix: str = "/api") -> Path:
    """Persist SDK config to the default config path.

    Args:
        base_url: Backend base URL.
        api_token: API token string.
        api_prefix: API path prefix, e.g. "/api". Use empty string for no prefix.

    Example:
        save_config("http://127.0.0.1:8000", "my-token")
    """
    config_dir = Path(CONFIG_DIR)
    config_path = Path(CONFIG_PATH)

    config_dir.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "base_url": base_url,
                "api_token": api_token,
                "api_prefix": normalize_api_prefix(api_prefix),
            },
            handle,
        )
    return config_path
