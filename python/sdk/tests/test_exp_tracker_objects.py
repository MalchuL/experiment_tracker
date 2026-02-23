from types import SimpleNamespace

from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeObjectsFactory:
    def log_object(self, experiment_id, request):
        return SimpleNamespace(experiment_id=experiment_id, request=request)


class _FakeAPI:
    def __init__(self):
        self.objects = _FakeObjectsFactory()
        self.uploaded: list[tuple[str, str, bytes, str]] = []
        self.queued: list[object] = []

    def check_blobs(self, hashes: list[str]):
        return {"missing": hashes}

    def upload_blob(
        self, blob_hash: str, file_name: str, file_content: bytes, content_type: str
    ):
        self.uploaded.append((blob_hash, file_name, file_content, content_type))
        return {"status": "ok"}

    def queued_request(self, request_spec):
        self.queued.append(request_spec)


def test_add_text_uploads_and_queues_object() -> None:
    api = _FakeAPI()
    tracker = ExpTracker("exp-id", "proj-id", api)  # type: ignore[arg-type]

    tracker.add_text("summary", "hello world", global_step=7)

    assert len(api.uploaded) == 1
    assert len(api.queued) == 1
    _, file_name, file_content, content_type = api.uploaded[0]
    assert file_name.startswith("summary_7")
    assert file_content == b"hello world"
    assert content_type == "text/plain"
