"""Static defaults for API base URL and path prefix.

These values remain the fallbacks when no config file or ``EXP_TRACKER_*``
environment variable supplies a value.
"""

DEFAULT_BASE_URL: str = "http://127.0.0.1:8000"
DEFAULT_API_PREFIX: str = "/api"
DEFAULT_HISTOGRAM_METADATA_BINS: int = 32
DEFAULT_SCATTER_METADATA_MAX_POINTS: int = 500
DEFAULT_SNAPSHOT_MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
