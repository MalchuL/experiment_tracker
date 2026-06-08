from pathlib import Path

import tomllib

import experiment_tracker_sdk


def test_runtime_and_package_versions_match() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    version = tomllib.loads(pyproject.read_text())["project"]["version"]

    assert experiment_tracker_sdk.__version__ == version == "0.11.9"
