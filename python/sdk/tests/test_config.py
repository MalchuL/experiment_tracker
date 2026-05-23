import pytest

from experiment_tracker_sdk import config as sdk_config


def test_save_and_load_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"

    monkeypatch.setattr(sdk_config, "CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(sdk_config, "CONFIG_PATH", str(config_path))

    sdk_config.save_config(base_url="http://localhost:8000", api_token="pat_test")
    loaded = sdk_config.load_config()

    assert loaded is not None
    assert loaded.base_url == "http://localhost:8000"
    assert loaded.api_token == "pat_test"


def test_exp_tracker_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    monkeypatch.setenv("EXP_TRACKER_DEFAULT_BASE_URL", "http://from-env.example")
    monkeypatch.setenv("EXP_TRACKER_DEFAULT_API_PREFIX", "/v1")
    assert get_exp_tracker_settings().default_base_url == "http://from-env.example"
    assert get_exp_tracker_settings().default_api_prefix == "/v1"
