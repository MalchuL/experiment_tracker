from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeAPI:
    def __init__(self):
        self.uploaded: list[tuple[str, bytes, str, str, dict]] = []
        self.final_uploaded: list[tuple[str, str, str, bytes, str]] = []

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict | None = None,
        tags: list | None = None,
    ):
        self.uploaded.append(
            (filename, content, content_type, name, metadata or {})
        )
        return {"status": "logged"}

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str,
        filename: str,
        content: bytes,
        content_type: str,
        name: str | None = None,
    ):
        self.final_uploaded.append(
            (name, filepath, filename, content, content_type)
        )
        return {"status": "upserted"}


def test_add_text_uploads_and_queues_object() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]

    tracker.add_text("summary", "hello world", global_step=7)

    assert len(api.uploaded) == 1
    filename, content, content_type, name, metadata = api.uploaded[0]
    assert filename.startswith("summary_7")
    assert content == b"hello world"
    assert content_type == "text/plain"
    assert name == "summary"


def test_log_final_artifact_uploads_without_step_suffix() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]

    tracker.log_final_artifact("config", "learning_rate: 0.01", default_extension=".yaml")

    assert len(api.final_uploaded) == 1
    name, filepath, filename, content, content_type = api.final_uploaded[0]
    assert name == "config"
    assert filepath == "final/config.yaml"
    assert filename == "config.yaml"
    assert content == b"learning_rate: 0.01"
    assert content_type == "text/plain"
