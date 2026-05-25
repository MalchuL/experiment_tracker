from datetime import datetime

from experiment_tracker_sdk.client.constants import UNSET
from experiment_tracker_sdk.client.domain.experiments.dto import ExperimentResponse
from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeScalarsService:
    def __init__(self):
        self.batch_calls: list[tuple[str, list[object]]] = []

    def log_scalars_batch(self, experiment_id: str, scalars: list[object]):
        self.batch_calls.append((experiment_id, list(scalars)))
        return {"kind": "scalars_batch_request", "scalars": list(scalars)}


class _FakeMetricsService:
    def __init__(self):
        self.calls: list[tuple[str, str, float, str | None]] = []

    def upsert_metric(
        self,
        experiment_id: str,
        name: str,
        value: float,
        label: str | None = None,
    ):
        self.calls.append((experiment_id, name, value, label))
        return {"kind": "metric_request"}


class _FakeExperimentsService:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, object]]] = []

    def update_experiment(self, experiment_id: str, **kwargs):
        kwargs = {key: value for key, value in kwargs.items() if value is not UNSET}
        self.calls.append((experiment_id, kwargs))
        return {"kind": "experiment_request", "experiment_id": experiment_id, **kwargs}


class _FakeRegistry:
    def __init__(self):
        self.scalars = _FakeScalarsService()
        self.metrics = _FakeMetricsService()
        self.experiments = _FakeExperimentsService()


class _FakeClient:
    def __init__(self):
        self.request_calls: list[object] = []
        self.queued_calls: list[object] = []

    def request(self, request_spec):
        self.request_calls.append(request_spec)
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
        self.queued_calls.append(request_spec)

    def flush(self):
        pass

    def close(self):
        pass


def _create_tracker() -> tuple[ExpTracker, _FakeRegistry, _FakeClient]:
    registry = _FakeRegistry()
    client = _FakeClient()
    tracker = ExpTracker(
        "exp-id",
        "proj-id",
        registry,  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
    )
    return tracker, registry, client


class _FakeTimer:
    def __init__(self, interval: float, callback):
        self.interval = interval
        self.callback = callback
        self.daemon = False
        self.cancelled = False
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.callback()


def _capture_timers(monkeypatch):
    import experiment_tracker_sdk.client.scalar_batching_strategy as scalar_batching

    timers: list[_FakeTimer] = []

    def create_timer(interval: float, callback):
        timer = _FakeTimer(interval, callback)
        timers.append(timer)
        return timer

    monkeypatch.setattr(scalar_batching, "Timer", create_timer)
    return timers


def test_add_metric_is_sync_and_uses_label() -> None:
    tracker, registry, client = _create_tracker()

    tracker.add_metric(name="accuracy", value=0.97, label="dataset/train")

    assert registry.metrics.calls == [("exp-id", "accuracy", 0.97, "dataset/train")]
    assert len(client.request_calls) == 1
    assert client.queued_calls == []


def test_features_updates_experiment_feature_tree() -> None:
    tracker, registry, client = _create_tracker()
    features = [
        {
            "name": "training",
            "children": [{"name": "optimizer-adam"}],
        }
    ]

    tracker.features(features)

    assert registry.experiments.calls == [("exp-id", {"features": features})]
    assert len(client.request_calls) == 1
    assert client.queued_calls == []


def test_add_scalar_queues_batch_after_128_steps(monkeypatch) -> None:
    timers = _capture_timers(monkeypatch)
    tracker, registry, client = _create_tracker()

    for step in range(257):
        tracker.add_scalar("loss", float(step), global_step=step)

    assert len(registry.scalars.batch_calls) == 1
    experiment_id, scalars = registry.scalars.batch_calls[0]
    assert experiment_id == "exp-id"
    assert len(scalars) == 256
    assert scalars[0].step == 0
    assert scalars[0].scalars == {"loss": 0.0}
    assert scalars[-1].step == 255
    assert scalars[-1].scalars == {"loss": 255.0}
    assert len(client.queued_calls) == 1
    assert timers[0].cancelled is True


def test_add_scalar_queues_batch_automatically_after_five_seconds(monkeypatch) -> None:
    timers = _capture_timers(monkeypatch)
    tracker, registry, client = _create_tracker()

    tracker.add_scalar("loss", 1.0, global_step=0)
    tracker.add_scalar("loss", 2.0, global_step=1)

    assert len(registry.scalars.batch_calls) == 0
    assert len(timers) == 1
    assert timers[0].interval == 5.0

    timers[0].fire()

    assert len(registry.scalars.batch_calls) == 1
    _, scalars = registry.scalars.batch_calls[0]
    assert [row.step for row in scalars] == [0, 1]
    assert [row.scalars for row in scalars] == [{"loss": 1.0}, {"loss": 2.0}]
    assert len(client.queued_calls) == 1


def test_flush_drains_current_scalar_batch(monkeypatch) -> None:
    _capture_timers(monkeypatch)
    tracker, registry, _client = _create_tracker()

    tracker.add_scalar("loss", 1.0, global_step=0)
    tracker.add_scalar("accuracy", 0.5, global_step=0)
    tracker.flush()

    assert len(registry.scalars.batch_calls) == 1
    _, scalars = registry.scalars.batch_calls[0]
    assert len(scalars) == 1
    assert scalars[0].step == 0
    assert scalars[0].scalars == {"loss": 1.0, "accuracy": 0.5}
