import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from experiment_tracker_sdk import config as sdk_config
from experiment_tracker_sdk.console import commands
from experiment_tracker_sdk.console.commands import cli


def test_save_and_load_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"

    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))

    sdk_config.save_config(base_url="http://localhost:8000", api_token="pat_test")
    loaded = sdk_config.load_config()

    assert loaded is not None
    assert loaded.base_url == "http://localhost:8000"
    assert loaded.api_token == "pat_test"


def test_exp_tracker_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify environment variables populate SDK runtime settings.

    Args:
        monkeypatch: Pytest helper used to set base URL, API prefix, and
            snapshot size environment variables.

    Returns:
        None. The assertions check the parsed settings values.
    """
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    monkeypatch.setenv("EXP_TRACKER_BASE_URL", "http://from-env.example")
    monkeypatch.setenv("EXP_TRACKER_API_PREFIX", "/v1")
    monkeypatch.setenv("EXP_TRACKER_SNAPSHOT_MAX_FILE_SIZE", "123")
    assert get_exp_tracker_settings().base_url == "http://from-env.example"
    assert get_exp_tracker_settings().api_prefix == "/v1"
    assert get_exp_tracker_settings().snapshot_max_file_size == 123


def test_exp_tracker_settings_allows_unlimited_snapshot_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify SDK settings preserve ``-1`` as unlimited snapshot size.

    Args:
        monkeypatch: Pytest helper used to set the environment variable.

    Returns:
        None. The assertion checks the parsed settings value.
    """
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    monkeypatch.setenv("EXP_TRACKER_SNAPSHOT_MAX_FILE_SIZE", "-1")

    assert get_exp_tracker_settings().snapshot_max_file_size == -1


def test_exp_tracker_settings_reads_num_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify worker count is loaded from the environment."""
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    monkeypatch.setenv("EXP_TRACKER_NUM_WORKERS", "8")

    assert get_exp_tracker_settings().num_workers == 8


def test_exp_tracker_settings_defaults_num_workers_to_min_four_cpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify default workers use ``min(4, cpu_count)``."""
    import os

    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    monkeypatch.delenv("EXP_TRACKER_NUM_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 16)

    assert get_exp_tracker_settings().num_workers == 4


def test_exp_tracker_settings_reads_config_path_and_api_token(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    config_path = tmp_path / "custom-config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("EXP_TRACKER_API_TOKEN", "pat_env_1234567890_tail")

    settings = get_exp_tracker_settings()

    assert settings.config_path == config_path
    assert settings.api_token == "pat_env_1234567890_tail"


def test_load_config_prefers_settings_over_config(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))

    sdk_config.save_config(
        base_url="http://localhost:8000",
        api_token="pat_file",
        api_prefix="/file-api",
    )

    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    get_exp_tracker_settings.cache_clear()
    monkeypatch.setenv("EXP_TRACKER_BASE_URL", "http://runtime.example")
    monkeypatch.setenv("EXP_TRACKER_API_PREFIX", "runtime-api")
    monkeypatch.setenv("EXP_TRACKER_API_TOKEN", "pat_env")

    loaded = sdk_config.load_config()

    assert loaded.base_url == "http://runtime.example"
    assert loaded.api_prefix == "/runtime-api"
    assert loaded.api_token == "pat_env"


def test_init_command_shows_defaults_and_uses_empty_input(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("EXP_TRACKER_BASE_URL", "http://from-env.example")
    monkeypatch.setenv("EXP_TRACKER_API_PREFIX", "/v2")
    monkeypatch.setenv("EXP_TRACKER_API_TOKEN", "pat_env_1234567890_tail")

    result = CliRunner().invoke(cli, ["init"], input="\n\n\n")

    assert result.exit_code == 0
    assert "Base URL (default: http://from-env.example):" in result.output
    assert "API prefix (default: /v2):" in result.output
    assert "API token (default: pat_env*********90_tail):" in result.output

    loaded = sdk_config.load_config()
    assert loaded.base_url == "http://from-env.example"
    assert loaded.api_prefix == "/v2"
    assert loaded.api_token == "pat_env_1234567890_tail"


def test_init_command_flags_skip_prompts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("EXP_TRACKER_BASE_URL", "http://from-env.example")
    monkeypatch.setenv("EXP_TRACKER_API_PREFIX", "/v2")
    monkeypatch.setenv("EXP_TRACKER_API_TOKEN", "pat_env_1234567890_tail")

    result = CliRunner().invoke(
        cli,
        [
            "init",
            "--base-url",
            "http://from-flag.example",
            "--api-prefix",
            "",
            "--api-token",
            "pat_from_flag",
        ],
    )

    assert result.exit_code == 0
    assert "Base URL" not in result.output
    assert "API prefix" not in result.output
    assert "API token" not in result.output

    loaded = sdk_config.load_config()
    assert loaded.base_url == "http://from-env.example"
    assert loaded.api_prefix == "/v2"
    assert loaded.api_token == "pat_env_1234567890_tail"

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    assert raw["base_url"] == "http://from-flag.example"
    assert raw["api_token"] == "pat_from_flag"
    assert raw["api_prefix"] == ""


def test_init_command_uses_existing_config_as_prompt_defaults(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))

    config_path.write_text(
        json.dumps(
            {
                "base_url": "http://from-file.example",
                "api_prefix": "/file-api",
                "api_token": "pat_file_1234567890_tail",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["init"], input="\n\n\n")

    assert result.exit_code == 0
    assert "Base URL (default: http://from-file.example):" in result.output
    assert "API prefix (default: /file-api):" in result.output
    assert "API token (default: pat_fil**********90_tail):" in result.output

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    assert raw["base_url"] == "http://from-file.example"
    assert raw["api_prefix"] == "/file-api"
    assert raw["api_token"] == "pat_file_1234567890_tail"


def test_init_command_falls_back_to_settings_when_existing_config_is_invalid(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("EXP_TRACKER_BASE_URL", "http://from-env.example")
    monkeypatch.setenv("EXP_TRACKER_API_PREFIX", "/v2")
    monkeypatch.setenv("EXP_TRACKER_API_TOKEN", "pat_env_1234567890_tail")

    config_path.write_text("{not-json", encoding="utf-8")

    result = CliRunner().invoke(cli, ["init"], input="\n\n\n")

    assert result.exit_code == 0
    assert "Base URL (default: http://from-env.example):" in result.output
    assert "API prefix (default: /v2):" in result.output
    assert "API token (default: pat_env*********90_tail):" in result.output


def test_init_ignore_command_creates_default_file() -> None:
    """Verify ``init-ignore`` writes the default snapshot ignore file.

    Args:
        None. The test uses Click's isolated filesystem.

    Returns:
        None. The assertions check command success and key default patterns.
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init-ignore"])

        assert result.exit_code == 0
        content = Path(".exp_tracker_ignore").read_text(encoding="utf-8")
        assert ".venv/" in content
        assert ".env" in content
        assert "logs/" in content


def test_check_files_show_skipped_prints_reasons() -> None:
    """Verify ``check-files --show-skipped`` includes skip reasons and sizes.

    Args:
        None. The test creates files inside Click's isolated filesystem.

    Returns:
        None. The assertions check ignored and oversized entries in CLI output.
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path(".exp_tracker_ignore").write_text("ignored.txt\n", encoding="utf-8")
        Path("ignored.txt").write_text("skip", encoding="utf-8")
        Path("large.txt").write_text("123456", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "check-files",
                "--max-file-size",
                "5",
                "--show-skipped",
                ".",
            ],
        )

        assert result.exit_code == 0
        assert "ignored\t.exp_tracker_ignore" in result.output
        assert "ignored\tignored.txt" in result.output
        assert "too_large\tlarge.txt\t6" in result.output


def test_init_command_can_create_ignore_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ``init --create-ignore-file`` creates ``.exp_tracker_ignore``.

    Args:
        tmp_path: Temporary path used for the SDK config file location.
        monkeypatch: Pytest helper used to point settings at that config path.

    Returns:
        None. The assertions check command success and ignore-file creation.
    """
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(config_path))

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--base-url",
                "http://localhost:8000",
                "--api-prefix",
                "/api",
                "--api-token",
                "pat_token",
                "--create-ignore-file",
            ],
        )

        assert result.exit_code == 0
        assert Path(".exp_tracker_ignore").is_file()


def test_clean_config_requires_confirmation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("EXP_TRACKER_CONFIG_PATH", raising=False)
    monkeypatch.setattr(commands, "DEFAULT_CONFIG_DIR", config_dir)

    result = CliRunner().invoke(cli, ["clean-config"], input="n\n")

    assert result.exit_code != 0
    assert config_dir.exists()


def test_clean_config_removes_config_dir_when_approved(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "config"
    nested = config_dir / "nested"
    nested.mkdir(parents=True)
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (nested / "state.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("EXP_TRACKER_CONFIG_PATH", raising=False)
    monkeypatch.setattr(commands, "DEFAULT_CONFIG_DIR", config_dir)

    result = CliRunner().invoke(cli, ["clean-config"], input="y\n")

    assert result.exit_code == 0
    assert f"Config directory removed: {config_dir}" in result.output
    assert not config_dir.exists()


def test_clean_config_does_not_remove_when_config_path_env_is_set(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "default-config"
    custom_dir = tmp_path / "custom-config"
    config_dir.mkdir()
    custom_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    custom_path = custom_dir / "config.json"
    custom_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("EXP_TRACKER_CONFIG_PATH", str(custom_path))
    monkeypatch.setattr(commands, "DEFAULT_CONFIG_DIR", config_dir)

    result = CliRunner().invoke(cli, ["clean-config"], input="y\n")

    assert result.exit_code == 0
    assert "EXP_TRACKER_CONFIG_PATH is set" in result.output
    assert config_dir.exists()
    assert custom_dir.exists()
