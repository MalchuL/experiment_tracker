"""Static defaults for API base URL and path prefix.

These values seed :class:`~experiment_tracker_sdk.settings.ExpTrackerSettings`
and remain the fallbacks when no ``EXP_TRACKER_*`` environment variables are
set. Override defaults for interactive ``experiment-tracker init`` prompts
via ``EXP_TRACKER_DEFAULT_BASE_URL`` and ``EXP_TRACKER_DEFAULT_API_PREFIX``.
"""

DEFAULT_BASE_URL: str = "http://127.0.0.1:8000"
DEFAULT_API_PREFIX: str = "/api"
