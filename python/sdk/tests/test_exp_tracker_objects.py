from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeAPI:
    def __init__(self):
        self.uploaded: list[tuple[str, str, bytes, str, dict]] = []

    def upload_and_log_artifact(
        self,
        project_id: str,
        experiment_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict | None = None,
        tags: list | None = None,
    ):
        self.uploaded.append(
            (file_name, file_content, content_type, name, metadata or {})
        )
        return {"status": "logged"}


def test_add_text_uploads_and_queues_object() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]

    tracker.add_text("summary", "hello world", global_step=7)

    assert len(api.uploaded) == 1
    file_name, file_content, content_type, name, metadata = api.uploaded[0]
    assert file_name.startswith("summary_7")
    assert file_content == b"hello world"
    assert content_type == "text/plain"
    assert name == "summary"
