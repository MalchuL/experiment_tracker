from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeMetricsService:
    def __init__(self):
        self.calls: list[tuple[str, str, float, int, str | None]] = []

    def create_metric(
        self,
        experiment_id: str,
        name: str,
        value: float,
        step: int = 0,
        label: str | None = None,
    ):
        self.calls.append((experiment_id, name, value, step, label))
        return {"kind": "metric_request"}


class _FakeAPI:
    def __init__(self):
        self.metrics = _FakeMetricsService()
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

    tracker.add_metric(name="accuracy", value=0.97, step=12, label="dataset/train")

    assert api.metrics.calls == [("exp-id", "accuracy", 0.97, 12, "dataset/train")]
    assert len(api.request_calls) == 1
    assert api.queued_calls == []
