"""Environment-driven settings (``EXP_TRACKER_*``) for SDK tooling."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONFIG_DIR = Path.home() / ".experiment-tracker"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"


class ExpTrackerSettings(BaseSettings):
    """Settings loaded from the environment and optional ``.env`` file.

    All variables use the ``EXP_TRACKER_`` prefix, for example
    ``EXP_TRACKER_BASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_prefix="EXP_TRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str | None = Field(
        default=None,
        description="Backend base URL override used instead of the config file value.",
    )
    api_prefix: str | None = Field(
        default=None,
        description="API path prefix override used instead of the config file value.",
    )
    config_path: Path = Field(
        default=DEFAULT_CONFIG_PATH,
        description="Path to the SDK config file used by ``load_config``.",
    )
    api_token: str | None = Field(
        default=None,
        description="API token override used instead of the token in the config file.",
    )


@lru_cache(maxsize=1)
def get_exp_tracker_settings() -> ExpTrackerSettings:
    """Return cached settings (reads ``.env`` / environment once per process)."""
    return ExpTrackerSettings()
