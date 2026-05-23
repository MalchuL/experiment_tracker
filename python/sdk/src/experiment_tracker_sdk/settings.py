"""Environment-driven defaults (``EXP_TRACKER_*``) for SDK tooling."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import DEFAULT_API_PREFIX, DEFAULT_BASE_URL


class ExpTrackerSettings(BaseSettings):
    """Settings loaded from the environment and optional ``.env`` file.

    All variables use the ``EXP_TRACKER_`` prefix, for example
    ``EXP_TRACKER_DEFAULT_BASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_prefix="EXP_TRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_base_url: str = Field(
        default=DEFAULT_BASE_URL,
        description=(
            "Default backend base URL for ``experiment-tracker init`` when "
            "``--base-url`` is omitted and the user accepts the empty default "
            "at the prompt."
        ),
    )
    default_api_prefix: str = Field(
        default=DEFAULT_API_PREFIX,
        description=(
            "Default API path prefix for ``experiment-tracker init`` when "
            "``--api-prefix`` is omitted and the user accepts the empty default "
            "at the prompt (e.g. ``/api``)."
        ),
    )


@lru_cache(maxsize=1)
def get_exp_tracker_settings() -> ExpTrackerSettings:
    """Return cached settings (reads ``.env`` / environment once per process)."""
    return ExpTrackerSettings()


@dataclass(frozen=True)
class CliInitDefaults:
    """Resolved defaults for ``experiment-tracker init`` interactive prompts."""

    default_base_url: str
    default_api_prefix: str


def get_cli_init_defaults() -> CliInitDefaults:
    """Return init prompt defaults (honours ``EXP_TRACKER_*`` / ``.env``)."""
    s = get_exp_tracker_settings()
    return CliInitDefaults(
        default_base_url=s.default_base_url,
        default_api_prefix=s.default_api_prefix,
    )
