from __future__ import annotations


def test_runner_init_sets_random_tracker_color(monkeypatch) -> None:
    from types import SimpleNamespace

    from experiment_tracker_sdk.console.utils.run import runner as runner_module
    from experiment_tracker_sdk.console.utils.run.runner import RunSample

    events = []

    class FakeStrategy:
        def __init__(self, **kwargs) -> None:
            pass

        def init(self, **kwargs):
            return SimpleNamespace(
                experiment=SimpleNamespace(id="experiment-1"),
                project=SimpleNamespace(id="project-1"),
            )

    class FakeTracker:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            events.append(("enter", None))
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

        def color(self, value) -> None:
            events.append(("color", value))

    import experiment_tracker_sdk.utils.color_utils as color_utils_module

    monkeypatch.setattr(runner_module, "ExperimentInitStrategy", FakeStrategy)
    monkeypatch.setattr(runner_module, "ExpTracker", FakeTracker)
    monkeypatch.setattr(
        color_utils_module.random, "randint", lambda start, end: 255
    )

    runner = RunSample(
        request_client=SimpleNamespace(),
        api_requests_registry=SimpleNamespace(),
    )

    runner.init(
        experiment_name_or_id="experiment",
        project_name_or_id="project",
    )

    assert events == [("enter", None), ("color", "#0000ff"), ("exit", None)]


def test_runner_mark_completed_updates_tracker_status_and_progress() -> None:
    from experiment_tracker_sdk.console.utils.run.runner import RunSample

    events = []
    runner = object.__new__(RunSample)

    class FakeTracker:
        def __enter__(self):
            events.append(("enter", None))
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

        def progress(self, value) -> None:
            events.append(("progress", value))

        def status(self, value) -> None:
            events.append(("status", value))

    runner.exp_tracker = FakeTracker()

    runner.mark_completed()

    assert events == [
        ("enter", None),
        ("progress", 100),
        ("status", "complete"),
        ("exit", None),
    ]


def test_runner_mark_failed_updates_tracker_status() -> None:
    from experiment_tracker_sdk.console.utils.run.runner import RunSample

    events = []
    runner = object.__new__(RunSample)

    class FakeTracker:
        def __enter__(self):
            events.append(("enter", None))
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

        def status(self, value) -> None:
            events.append(("status", value))

    runner.exp_tracker = FakeTracker()

    runner.mark_failed()

    assert events == [("enter", None), ("status", "failed"), ("exit", None)]


def test_runner_mark_methods_ignore_uninitialized_tracker() -> None:
    from experiment_tracker_sdk.console.utils.run.runner import RunSample

    runner = object.__new__(RunSample)
    runner.exp_tracker = None

    runner.mark_completed()
    runner.mark_failed()
