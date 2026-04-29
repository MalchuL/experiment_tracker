"""Startup logging for admin panel key (never log non-default secret values)."""

import logging

from config.settings import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_INSECURE_KEY = "admin"


def log_admin_panel_key_startup() -> None:
    settings = get_settings()
    if settings.admin_panel_key == _DEFAULT_INSECURE_KEY:
        logger.warning(
            "ADMIN_PANEL_KEY is unset or set to the default insecure value %r. "
            "The admin HTTP API accepts X-Admin-Key: %s. Set ADMIN_PANEL_KEY to a strong "
            "random secret in production.",
            _DEFAULT_INSECURE_KEY,
            _DEFAULT_INSECURE_KEY,
        )
    else:
        logger.info(
            "Admin panel HTTP API is enabled; key was loaded from environment variable "
            "ADMIN_PANEL_KEY (value not logged)."
        )
