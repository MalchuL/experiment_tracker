from datetime import datetime

from experiment_tracker_sdk.client.constants import UNSET
from experiment_tracker_sdk.client.domain.experiments.dto import ExperimentResponse
from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeExperimentsService:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, object]]] = []

    def update_experiment(self, experiment_id: str, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not UNSET}
        self.calls.append((experiment_id, kwargs))
        return {"kind": "experiment_request", "experiment_id": experiment_id, **kwargs}


class _FakeRegistry:
    def __init__(self):
        self.experiments = _FakeExperimentsService()


class _FakeClient:
    def request(self, request_spec):
        if (
            isinstance(request_spec, dict)
            and request_spec.get("kind") == "experiment_request"
        ):
            return ExperimentResponse(
                id=request_spec["experiment_id"],
                projectId="proj-id",
                name=request_spec.get("name", ""),
                description=request_spec.get("description", ""),
                status=str(request_spec.get("status", "planned")),
                features=request_spec.get("features", []),
                progress=request_spec.get("progress"),
                tags=request_spec.get("tags"),
                createdAt=datetime(2026, 1, 1),
            )
        return {"status": "ok"}

    def queued_request(self, request_spec):
        _ = request_spec

    def flush(self):
        pass

    def close(self):
        pass


def _create_tracker() -> tuple[ExpTracker, _FakeRegistry]:
    registry = _FakeRegistry()
    client = _FakeClient()
    tracker = ExpTracker(
        "exp-id",
        "proj-id",
        registry,  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
    )
    return tracker, registry


def test_progress_rounds_float_fractions() -> None:
    tracker, registry = _create_tracker()

    with tracker:
        tracker.progress(0.0)
    assert registry.experiments.calls[-1][1]["progress"] == 0

    with tracker:
        tracker.progress(0.5)
    assert registry.experiments.calls[-1][1]["progress"] == 50

    with tracker:
        tracker.progress(1.0)
    assert registry.experiments.calls[-1][1]["progress"] == 100

    with tracker:
        tracker.progress(0.255)
    assert registry.experiments.calls[-1][1]["progress"] == 26


def test_progress_clamps_out_of_range_floats_before_rounding() -> None:
    tracker, registry = _create_tracker()

    with tracker:
        tracker.progress(-0.5)
    assert registry.experiments.calls[-1][1]["progress"] == 0

    with tracker:
        tracker.progress(1.5)
    assert registry.experiments.calls[-1][1]["progress"] == 100


def test_progress_clamps_out_of_range_ints() -> None:
    tracker, registry = _create_tracker()

    with tracker:
        tracker.progress(-10)
    assert registry.experiments.calls[-1][1]["progress"] == 0

    with tracker:
        tracker.progress(150)
    assert registry.experiments.calls[-1][1]["progress"] == 100
