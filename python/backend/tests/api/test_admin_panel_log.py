import logging

import pytest

from api.admin_panel_log import log_admin_panel_key_startup
from config.settings import get_settings


def test_startup_log_default_key(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ADMIN_PANEL_KEY", raising=False)
    get_settings.cache_clear()
    caplog.set_level(logging.WARNING)
    log_admin_panel_key_startup()
    assert "default insecure" in caplog.text.lower() or "admin" in caplog.text
    get_settings.cache_clear()


def test_startup_log_custom_key(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_PANEL_KEY", "not-the-default-secret")
    get_settings.cache_clear()
    caplog.set_level(logging.INFO)
    log_admin_panel_key_startup()
    assert "ADMIN_PANEL_KEY" in caplog.text
    assert "not-the-default-secret" not in caplog.text
    get_settings.cache_clear()
