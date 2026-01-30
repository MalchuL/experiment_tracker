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
