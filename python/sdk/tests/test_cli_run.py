from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_split_on_first_double_dash() -> None:
    from experiment_tracker_sdk.console.utils.argv import split_on_first_double_dash

    assert split_on_first_double_dash(["a", "--", "b"]) == (["a"], ["b"])
    assert split_on_first_double_dash(["a", "b"]) == (["a", "b"], [])
    assert split_on_first_double_dash([]) == ([], [])


def test_run_executes_as_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "entry.py"
    script.write_text(
        "import json, sys\n"
        "assert __name__ == '__main__'\n"
        "path = __import__('pathlib').Path('out.json')\n"
        "path.write_text(json.dumps(sys.argv))\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["experiment-tracker", "run", str(script)])
    from experiment_tracker_sdk.cli import main

    main()
    data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert data == [str(script)]


def test_run_forwards_argv_after_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path('out.json').write_text(json.dumps(sys.argv))\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "experiment-tracker",
            "run",
            "--project",
            "p1",
            "--offline",
            str(script),
            "--",
            "--epochs",
            "10",
        ],
    )
    from experiment_tracker_sdk.cli import main

    main()
    data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert data[0] == str(script)
    assert data[1:] == ["--epochs", "10"]


def test_run_rejects_script_args_without_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", str(script), "--epochs", "10"],
    )
    from experiment_tracker_sdk.cli import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_run_missing_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["experiment-tracker", "run"])
    from experiment_tracker_sdk.cli import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_run_script_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "does_not_exist.py"],
    )
    from experiment_tracker_sdk.cli import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_cli_entrypoint_run_subprocess(tmp_path: Path) -> None:
    script = tmp_path / "m.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path('argv.json').write_text(json.dumps(sys.argv))\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiment_tracker_sdk.cli",
            "run",
            str(script),
            "--",
            "--x",
            "1",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads((tmp_path / "argv.json").read_text(encoding="utf-8"))
    assert data[0] == str(script)
    assert data[1:] == ["--x", "1"]
