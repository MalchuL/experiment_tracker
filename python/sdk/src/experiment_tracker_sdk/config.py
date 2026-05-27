import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from experiment_tracker_sdk.error import ExpTrackerConfigError

from .constants import DEFAULT_API_PREFIX
from .settings import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_PATH, get_exp_tracker_settings


@dataclass
class SDKConfig:
    base_url: str
    api_token: str
    api_prefix: str = DEFAULT_API_PREFIX


def normalize_api_prefix(api_prefix: str | None) -> str:
    if api_prefix is None:
        return DEFAULT_API_PREFIX
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
    return urlunsplit(
        (split.scheme, split.netloc, composed_path, split.query, split.fragment)
    )


def _load_config_file(config_path: Path) -> SDKConfig:
    """Load SDK config from a specific file path."""
    if not config_path.exists():
        raise ExpTrackerConfigError(f"Config file not found at path: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ExpTrackerConfigError(f"Config file is invalid: {config_path}")
    if not raw.get("base_url"):
        raise ExpTrackerConfigError(f"Config file is missing 'base_url': {config_path}")
    api_token = raw.get("api_token")
    if not api_token:
        raise ExpTrackerConfigError(
            f"Config file is missing 'api_token': {config_path}"
        )
    return SDKConfig(
        base_url=raw["base_url"],
        api_token=api_token,
        api_prefix=normalize_api_prefix(raw.get("api_prefix", DEFAULT_API_PREFIX)),
    )


def load_config() -> SDKConfig:
    """Load SDK config from disk.

    Returns:
        SDKConfig if present and valid, otherwise raises ExpTrackerConfigError.
    """
    settings = get_exp_tracker_settings()
    config = _load_config_file(Path(settings.config_path))
    return SDKConfig(
        base_url=settings.base_url or config.base_url,
        api_token=settings.api_token or config.api_token,
        api_prefix=(
            normalize_api_prefix(settings.api_prefix)
            if settings.api_prefix is not None
            else config.api_prefix
        ),
    )


def save_config(
    base_url: str,
    api_token: str,
    api_prefix: str = DEFAULT_API_PREFIX,
) -> Path:
    """Persist SDK config to the default config path.

    Args:
        base_url: Backend base URL.
        api_token: API token string.
        api_prefix: API path prefix, e.g. "/api". Use empty string for no prefix.

    Example:
        save_config("http://127.0.0.1:8000", "my-token")
    """
    config_path = Path(get_exp_tracker_settings().config_path)
    config_dir = config_path.parent

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
