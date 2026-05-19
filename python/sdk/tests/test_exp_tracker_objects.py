from experiment_tracker_sdk.exp_tracker import ExpTracker


class _FakeExperimentArtifactsService:
    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        file,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict | None = None,
        tags: list | None = None,
    ):
        return {
            "kind": "upload_at_step",
            "experiment_id": experiment_id,
            "file": file,
            "name": name,
            "artifact_type": artifact_type,
            "step": step,
            "metadata": metadata,
            "tags": tags,
        }

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str,
        file,
        name: str | None = None,
    ):
        return {
            "kind": "upsert_named",
            "experiment_id": experiment_id,
            "filepath": filepath,
            "file": file,
            "name": name,
        }


class _FakeRegistry:
    def __init__(self):
        self.experiment_artifacts = _FakeExperimentArtifactsService()


class _FakeClient:
    def __init__(self):
        self.uploaded: list[tuple[str, bytes, str, str, dict]] = []
        self.final_uploaded: list[tuple[str, str, str, bytes, str]] = []

    def request(self, request_spec):
        if request_spec["kind"] == "upload_at_step":
            file = request_spec["file"]
            self.uploaded.append(
                (
                    file.filename,
                    file.content,
                    file.content_type,
                    request_spec["name"],
                    request_spec["metadata"] or {},
                )
            )
            return {"status": "logged"}
        if request_spec["kind"] == "upsert_named":
            file = request_spec["file"]
            self.final_uploaded.append(
                (
                    request_spec["name"],
                    request_spec["filepath"],
                    file.filename,
                    file.content,
                    file.content_type,
                )
            )
            return {"status": "upserted"}
        raise AssertionError(f"Unexpected request: {request_spec}")

    def queued_request(self, request_spec):
        raise AssertionError(f"Unexpected queued request: {request_spec}")

    def flush(self):
        pass

    def close(self):
        pass


def _create_tracker() -> tuple[ExpTracker, _FakeClient]:
    client = _FakeClient()
    tracker = ExpTracker(
        "exp-id",
        "proj-id",
        _FakeRegistry(),  # type: ignore[arg-type]
        client,  # type: ignore[arg-type]
    )
    return tracker, client


def test_add_text_uploads_and_queues_object() -> None:
    tracker, client = _create_tracker()

    tracker.add_text("summary", "hello world", global_step=7)

    assert len(client.uploaded) == 1
    filename, content, content_type, name, metadata = client.uploaded[0]
    assert filename.startswith("summary_7")
    assert content == b"hello world"
    assert content_type == "text/plain"
    assert name == "summary"


def test_log_final_artifact_uploads_without_step_suffix() -> None:
    tracker, client = _create_tracker()

    tracker.log_final_artifact("config", "learning_rate: 0.01", default_extension=".yaml")

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "config"
    assert filepath == "final/config.yaml"
    assert filename == "config.yaml"
    assert content == b"learning_rate: 0.01"
    assert content_type == "text/plain"


def test_log_final_artifact_long_json_string_not_treated_as_path() -> None:
    """Regression: huge str payloads must not be passed to Path(...).exists() (ENAMETOOLONG)."""
    tracker, client = _create_tracker()

    payload = '{"k": "%s"}' % ("x" * 5000)
    tracker.log_final_artifact(
        "training_summary_json",
        payload,
        stored_filepath="final/summary.json",
        default_content_type="application/json",
        default_extension=".json",
    )

    assert len(client.final_uploaded) == 1
    name, filepath, filename, content, content_type = client.final_uploaded[0]
    assert name == "training_summary_json"
    assert filepath == "final/summary.json"
    assert content == payload.encode("utf-8")
    assert content_type == "application/json"
