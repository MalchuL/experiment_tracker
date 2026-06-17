"""Environment-driven settings (``EXP_TRACKER_*``) for SDK tooling."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from experiment_tracker_sdk.constants import (
    DEFAULT_HISTOGRAM_METADATA_BINS,
    DEFAULT_SCATTER_METADATA_MAX_POINTS,
    DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES,
)
from experiment_tracker_sdk.utils.parallel import default_parallel_worker_count

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
    histogram_metadata_bins: int = Field(
        default=DEFAULT_HISTOGRAM_METADATA_BINS,
        ge=1,
        description="Number of histogram bins stored in artifact metadata previews.",
    )
    scatter_metadata_max_points: int = Field(
        default=DEFAULT_SCATTER_METADATA_MAX_POINTS,
        ge=1,
        description="Maximum scatter points stored in artifact metadata previews.",
    )
    snapshot_max_file_size: int = Field(
        default=DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES,
        ge=-1,
        description=(
            "Maximum file size in bytes included in snapshots. Use -1 to disable."
        ),
    )
    num_workers: int = Field(
        default_factory=default_parallel_worker_count,
        ge=1,
        description=(
            "Number of parallel workers used when hashing and uploading snapshots."
        ),
    )


@lru_cache(maxsize=1)
def get_exp_tracker_settings() -> ExpTrackerSettings:
    """Return cached settings (reads ``.env`` / environment once per process)."""
    return ExpTrackerSettings()
