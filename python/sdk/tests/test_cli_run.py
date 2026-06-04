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
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "--offline", str(script)],
    )
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
            "--team",
            "t1",
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


def test_run_initializes_runner_when_experiment_is_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    calls = []
    tracker_events = []

    class FakeTracker:
        def progress(self, value) -> None:
            tracker_events.append(("progress", value))

        def status(self, value) -> None:
            tracker_events.append(("status", value))

    class FakeRunSample:
        exp_tracker = FakeTracker()

        def init(
            self,
            experiment_name_or_id,
            project_name_or_id=None,
            team_name_or_id=None,
            init_params=None,
        ) -> None:
            calls.append(
                {
                    "experiment": experiment_name_or_id,
                    "project": project_name_or_id,
                    "team": team_name_or_id,
                    "init_params": init_params,
                }
            )

        def mark_completed(self) -> None:
            self.exp_tracker.progress(100)
            self.exp_tracker.status("complete")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "experiment-tracker",
            "run",
            "--project",
            "p1",
            "--team",
            "t1",
            "--experiment",
            "e1",
            str(script),
        ],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    main()
    assert len(calls) == 1
    assert calls[0]["experiment"] == "e1"
    assert calls[0]["project"] == "p1"
    assert calls[0]["team"] == "t1"
    assert calls[0]["init_params"].create_team_if_not_exists is True
    assert calls[0]["init_params"].create_project_if_not_exists is True
    assert calls[0]["init_params"].create_experiment_if_not_exists is True
    assert tracker_events == [("progress", 100), ("status", "complete")]


def test_run_generates_experiment_name_and_default_project_when_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    calls = []

    class FakeRunSample:
        exp_tracker = None

        def init(
            self,
            experiment_name_or_id,
            project_name_or_id=None,
            team_name_or_id=None,
            init_params=None,
        ) -> None:
            calls.append(
                {
                    "experiment": experiment_name_or_id,
                    "project": project_name_or_id,
                    "team": team_name_or_id,
                }
            )

        def mark_completed(self) -> None:
            pass

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", str(script)],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    monkeypatch.setattr(
        run_module,
        "_default_experiment_name",
        lambda: "Experiment 26-05-2026 14:30:05",
    )
    from experiment_tracker_sdk.cli import main

    main()
    assert calls == [
        {
            "experiment": "Experiment 26-05-2026 14:30:05",
            "project": "Default",
            "team": None,
        }
    ]


def test_run_marks_runner_failed_when_script_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    tracker_events = []

    class FakeTracker:
        def progress(self, value) -> None:
            tracker_events.append(("progress", value))

        def status(self, value) -> None:
            tracker_events.append(("status", value))

    class FakeRunSample:
        exp_tracker = FakeTracker()

        def init(self, **kwargs) -> None:
            pass

        def mark_failed(self) -> None:
            self.exp_tracker.status("failed")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "experiment-tracker",
            "run",
            "--project",
            "p1",
            "--experiment",
            "e1",
            str(script),
        ],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    with pytest.raises(RuntimeError, match="boom"):
        main()
    assert tracker_events == [("status", "failed")]


def test_run_uses_default_project_when_experiment_is_provided_without_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    calls = []

    class FakeRunSample:
        exp_tracker = None

        def init(
            self,
            experiment_name_or_id,
            project_name_or_id=None,
            team_name_or_id=None,
            init_params=None,
        ) -> None:
            calls.append(
                {
                    "experiment": experiment_name_or_id,
                    "project": project_name_or_id,
                    "team": team_name_or_id,
                }
            )

        def mark_completed(self) -> None:
            pass

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "--experiment", "e1", str(script)],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    main()
    assert calls == [{"experiment": "e1", "project": "Default", "team": None}]


def test_run_snapshot_logs_before_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify ``run --snapshot`` logs files before marking completion.

    Args:
        tmp_path: Temporary directory used for the synthetic entry script.
        monkeypatch: Pytest helper used to patch argv, cwd, and runner class.

    Returns:
        None. The test asserts the fake runner call order.
    """
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    events = []

    class FakeRunSample:
        """Runner fake that records init, snapshot, and completion events.

        Args:
            None. Instances use the surrounding ``events`` list.

        Result:
            Test double compatible with the CLI runner contract.
        """

        exp_tracker = None

        def init(self, **_kwargs) -> None:
            """Record runner initialization.

            Args:
                **_kwargs: Initialization arguments forwarded by the CLI.

            Returns:
                None.
            """
            events.append(("init", None))

        def log_snapshot(self, path) -> None:
            """Record the snapshot path selected by the CLI.

            Args:
                path: Directory passed to ``RunSample.log_snapshot``.

            Returns:
                None.
            """
            events.append(("snapshot", path))

        def mark_completed(self) -> None:
            """Record successful script completion.

            Args:
                None.

            Returns:
                None.
            """
            events.append(("complete", None))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "--snapshot", str(script)],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    main()
    assert events == [
        ("init", None),
        ("snapshot", script.resolve().parent),
        ("complete", None),
    ]


def test_run_snapshot_forwards_unlimited_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify the CLI forwards ``-1`` as the unlimited snapshot size override.

    Args:
        tmp_path: Temporary directory used for the synthetic entry script.
        monkeypatch: Pytest helper used to patch argv, cwd, and runner class.

    Returns:
        None. The test asserts the snapshot call receives ``max_file_size=-1``.
    """
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    events = []

    class FakeRunSample:
        """Runner fake that records snapshot size arguments.

        Args:
            None. Instances use the surrounding ``events`` list.

        Result:
            Test double used to observe ``log_snapshot`` arguments.
        """

        exp_tracker = None

        def init(self, **_kwargs) -> None:
            """Accept CLI initialization without side effects.

            Args:
                **_kwargs: Initialization arguments forwarded by the CLI.

            Returns:
                None.
            """
            pass

        def log_snapshot(self, path, *, max_file_size) -> None:
            """Record snapshot path and explicit size limit.

            Args:
                path: Directory passed to ``RunSample.log_snapshot``.
                max_file_size: Size override forwarded from the CLI option.

            Returns:
                None.
            """
            events.append((path, max_file_size))

        def mark_completed(self) -> None:
            """Accept completion without side effects.

            Args:
                None.

            Returns:
                None.
            """
            pass

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "experiment-tracker",
            "run",
            "--snapshot",
            "--snapshot-max-file-size",
            "-1",
            str(script),
        ],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    main()
    assert events == [(script.resolve().parent, -1)]


def test_run_snapshot_rejects_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify snapshot logging is rejected for offline CLI runs.

    Args:
        tmp_path: Temporary directory used for the synthetic entry script.
        monkeypatch: Pytest helper used to patch argv and cwd.

    Returns:
        None. The test asserts Click exits with usage-error code ``2``.
    """
    script = tmp_path / "entry.py"
    script.write_text("print('x')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "--snapshot", "--offline", str(script)],
    )
    from experiment_tracker_sdk.cli import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_run_snapshot_not_called_when_script_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify failed scripts mark failure and skip snapshot logging.

    Args:
        tmp_path: Temporary directory used for a script that raises.
        monkeypatch: Pytest helper used to patch argv, cwd, and runner class.

    Returns:
        None. The test asserts only the failure marker is recorded.
    """
    script = tmp_path / "entry.py"
    script.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    events = []

    class FakeRunSample:
        """Runner fake that exposes failure and snapshot hooks.

        Args:
            None. Instances use the surrounding ``events`` list.

        Result:
            Test double used to verify error-path call ordering.
        """

        exp_tracker = None

        def init(self, **_kwargs) -> None:
            """Accept CLI initialization without side effects.

            Args:
                **_kwargs: Initialization arguments forwarded by the CLI.

            Returns:
                None.
            """
            pass

        def log_snapshot(self, path) -> None:
            """Record any unexpected snapshot call.

            Args:
                path: Directory passed to snapshot logging.

            Returns:
                None.
            """
            events.append(("snapshot", path))

        def mark_failed(self) -> None:
            """Record that the runner marked the experiment as failed.

            Args:
                None.

            Returns:
                None.
            """
            events.append(("failed", None))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["experiment-tracker", "run", "--snapshot", str(script)],
    )
    from experiment_tracker_sdk.console import run as run_module

    monkeypatch.setattr(run_module, "RunSample", FakeRunSample)
    from experiment_tracker_sdk.cli import main

    with pytest.raises(RuntimeError, match="boom"):
        main()
    assert events == [("failed", None)]


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
            "--offline",
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
