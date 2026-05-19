from experiment_tracker_sdk.exp_tracker import ExpTracker


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
        self.calls: list[tuple[str, list[dict[str, object]]]] = []

    def update_experiment(self, experiment_id: str, features):
        self.calls.append((experiment_id, features))
        return {"kind": "experiment_request"}


class _FakeAPI:
    def __init__(self):
        self.metrics = _FakeMetricsService()
        self.experiments = _FakeExperimentsService()
        self.request_calls: list[object] = []
        self.queued_calls: list[object] = []

    def request(self, request_spec):
        self.request_calls.append(request_spec)
        return {"status": "ok"}

    def queued_request(self, request_spec):
        self.queued_calls.append(request_spec)


def test_add_metric_is_sync_and_uses_label() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]

    tracker.add_metric(name="accuracy", value=0.97, label="dataset/train")

    assert api.metrics.calls == [("exp-id", "accuracy", 0.97, "dataset/train")]
    assert len(api.request_calls) == 1
    assert api.queued_calls == []


def test_features_updates_experiment_feature_tree() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]
    features = [
        {
            "name": "training",
            "children": [{"name": "optimizer-adam"}],
        }
    ]

    tracker.features(features)

    assert api.experiments.calls == [("exp-id", features)]
    assert len(api.request_calls) == 1
    assert api.queued_calls == []
