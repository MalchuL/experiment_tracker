import hashlib
from io import BytesIO
import os
from zipfile import ZipFile

import httpx
import pytest

from experiment_tracker_sdk.client import ArtifactClient

from conftest import call, eventually


@pytest.fixture
def artifacts(tracker):
    """Reuse the experiment tracker's authenticated client for artifact operations."""
    return ArtifactClient(tracker._api_requests_registry, tracker._request_client)


@pytest.fixture
def storage():
    """Provide a direct object-storage HTTP client and close it after the test."""
    with httpx.Client(
        base_url=os.environ["INTEGRATION_STORAGE_URL"] + "/",
        timeout=30,
        trust_env=False,
    ) as client:
        yield client


@pytest.fixture
def scalars():
    """Provide a direct scalars-service HTTP client and close it after the test."""
    with httpx.Client(
        base_url=os.environ["INTEGRATION_SCALARS_URL"] + "/",
        timeout=30,
        trust_env=False,
    ) as client:
        yield client


def test_step_artifact_metadata_and_bytes(api, project, experiment, artifacts):
    """Read back a step artifact's metadata, tags, size, and original bytes."""
    eid = experiment["id"]
    payload = b"A real training output\n"
    result = artifacts.upload_and_log_experiment_artifact_at_step(
        eid,
        "output.txt",
        payload,
        "text/plain",
        "train/output",
        "text",
        7,
        metadata={"caption": "Prediction"},
        tags=["train"],
    )
    assert result.status == "logged"
    info = eventually(
        lambda: call(
            api,
            "GET",
            f"experiment-artifacts/projects/{project['id']}/get-at-step",
            params={"experiment_id": eid, "step": 7},
        ),
        lambda data: bool(data["data"]) and bool(data["data"][0]["artifacts_info"]),
    )
    row = info["data"][0]["artifacts_info"][0]
    assert (row["name"], row["step"], row["tags"]) == ("train/output", 7, ["train"])
    assert row["metadata"]["caption"] == "Prediction"
    assert row["metadata"]["size_bytes"] == str(len(payload))
    assert (
        artifacts.download_experiment_artifact_at_step(eid, 7, "train/output").content
        == payload
    )


def test_deleted_step_artifact_download_returns_not_found(
    api, project, experiment, artifacts
):
    """Return 404 when downloading a step artifact after deletion by content hash."""
    eid = experiment["id"]
    artifacts.upload_and_log_experiment_artifact_at_step(
        eid, "output.txt", b"delete me", "text/plain", "train/output", "text", 7
    )
    info = call(
        api,
        "GET",
        f"experiment-artifacts/projects/{project['id']}/get-at-step",
        params={"experiment_id": eid, "step": 7},
    )
    row = info["data"][0]["artifacts_info"][0]
    call(
        api,
        "DELETE",
        f"experiment-artifacts/{eid}/at-step",
        params={"hash": row["path"]},
    )
    response = api.get(
        f"experiment-artifacts/{eid}/download-at-step",
        params={"step": 7, "name": "train/output"},
    )
    assert response.status_code == 404, response.text


def test_deleted_step_artifact_is_removed_from_index(
    api, project, experiment, artifacts
):
    """Remove deleted step artifacts from the scalars metadata index and its total."""
    eid = experiment["id"]
    artifacts.upload_and_log_experiment_artifact_at_step(
        eid, "output.txt", b"delete me", "text/plain", "train/output", "text", 7
    )
    path = f"experiment-artifacts/projects/{project['id']}/get-at-step"
    params = {"experiment_id": eid, "step": 7}
    row = call(api, "GET", path, params=params)["data"][0]["artifacts_info"][0]
    call(
        api,
        "DELETE",
        f"experiment-artifacts/{eid}/at-step",
        params={"hash": row["path"]},
    )
    info = eventually(
        lambda: call(api, "GET", path, params=params),
        lambda data: all(not item["artifacts_info"] for item in data["data"]),
    )
    assert info["total"] == 0


def test_named_artifact_replace_archive_and_delete(api, experiment, artifacts):
    """Replace a named file, verify ZIP contents, and delete only the selected file."""
    eid = experiment["id"]
    for filepath, content in (
        ("exports/config.txt", b"first"),
        ("exports/model.bin", b"weights"),
    ):
        artifacts.upsert_named_experiment_artifact(
            eid,
            filepath,
            filepath.split("/")[-1],
            content,
            "application/octet-stream",
            name="export",
        )
    artifacts.upsert_named_experiment_artifact(
        eid,
        "exports/config.txt",
        "config.txt",
        b"replacement",
        "text/plain",
        name="export",
    )
    listed = call(api, "GET", f"experiment-artifacts/experiments/{eid}")
    assert listed["total"] == 2
    assert {row["filepath"] for row in listed["data"]} == {
        "exports/config.txt",
        "exports/model.bin",
    }
    assert (
        artifacts.download_named_experiment_artifact(eid, "exports/config.txt").content
        == b"replacement"
    )
    response = api.get(
        "experiment-artifacts/download/archive",
        params={"experiment_id": eid, "name": "export"},
    )
    assert response.status_code == 200, response.text
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.read("exports/config.txt") == b"replacement"
        assert archive.read("exports/model.bin") == b"weights"
    call(
        api,
        "DELETE",
        "experiment-artifacts/delete",
        params={"experiment_id": eid, "filepath": "exports/config.txt"},
    )
    assert call(api, "GET", f"experiment-artifacts/experiments/{eid}")["total"] == 1


def test_project_cas_dedup_and_namespace_isolation(api, project, artifacts, storage):
    """Deduplicate project blobs by hash while keeping project namespaces independent."""
    pid = project["id"]
    payload = b"shared-dataset-content"
    digest = hashlib.sha256(payload).hexdigest()
    assert artifacts.check_project_artifacts(pid, [digest]).missing == [digest]
    assert (
        artifacts.upload_project_artifact(
            pid, "data.bin", payload, "application/octet-stream"
        ).detail
        == "uploaded"
    )
    assert (
        artifacts.upload_project_artifact(
            pid, "same.bin", payload, "application/octet-stream"
        ).detail
        == "exists"
    )
    response = api.get(f"project-artifacts/{pid}/artifacts/{digest}")
    assert response.status_code == 200 and response.content == payload
    usage = call(storage, "GET", f"project-artifacts/{pid}/usage")
    assert usage["projectArtifacts"]["count"] == 1
    other = call(api, "POST", "projects", json={"name": "Another CAS namespace"})
    assert artifacts.check_project_artifacts(other["id"], [digest]).missing == [digest]
    call(api, "DELETE", f"project-artifacts/{pid}/artifacts/{digest}")
    assert artifacts.check_project_artifacts(pid, [digest]).missing == [digest]


def test_sdk_project_blob_download_returns_bytes(project, artifacts):
    """Return the original project blob bytes through the SDK download helper."""
    payload = b"binary project blob"
    result = artifacts.upload_project_artifact(
        project["id"], "data.bin", payload, "application/octet-stream"
    )
    assert (
        artifacts.download_project_artifact(project["id"], result.hash).content
        == payload
    )


def test_snapshot_manifest_preview_archive_and_ignore_rules(
    api, tracker, experiment, tmp_path
):
    """Verify snapshot previews and ZIPs exclude ignored and oversized files."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "train.py").write_text("epochs = 2\n")
    (source / ".exp_tracker_ignore").write_text("ignored.bin\n")
    (source / "ignored.bin").write_bytes(b"secret")
    (source / "large.bin").write_bytes(b"x" * 1024)
    result = tracker.log_snapshot(source, root=source, max_file_size=100)
    assert result.snapshot_id
    eid = experiment["id"]
    manifest = call(api, "GET", f"experiments/{eid}/data/snapshot/files")
    paths = {entry["path"] for entry in manifest["files"]}
    assert (
        "train.py" in paths and "ignored.bin" not in paths and "large.bin" not in paths
    )
    entry = next(row for row in manifest["files"] if row["path"] == "train.py")
    preview = call(
        api,
        "POST",
        f"experiments/{eid}/data/snapshot/file",
        json={"path": entry["path"], "hash": entry["hash"]},
    )
    assert preview["content"] == "epochs = 2\n"
    response = api.get(f"experiments/{eid}/data/snapshot/download")
    assert response.status_code == 200, response.text
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.read("train.py") == b"epochs = 2\n"
        assert "ignored.bin" not in archive.namelist()
    invalid = api.post(
        f"experiments/{eid}/data/snapshot/file",
        json={"path": "../../outside.txt", "hash": entry["hash"]},
    )
    assert invalid.status_code in (400, 404), invalid.text


@pytest.mark.parametrize("filepath", ["../outside.txt", "/absolute.txt"])
def test_invalid_artifact_paths(api, experiment, filepath):
    """Reject traversal and absolute artifact paths without creating metadata rows."""
    response = api.post(
        "experiment-artifacts/upsert",
        data={"experiment_id": experiment["id"], "filepath": filepath},
        files={"file": ("data.txt", b"invalid", "text/plain")},
    )
    assert response.status_code == 400, response.text
    assert (
        call(api, "GET", f"experiment-artifacts/experiments/{experiment['id']}")[
            "total"
        ]
        == 0
    )


def test_experiment_category_cleanup_keeps_sibling_data(
    api, project, experiment, artifacts
):
    """Clear one run's artifacts and scalars while preserving it and sibling data."""
    eid, pid = experiment["id"], project["id"]
    sibling = call(
        api, "POST", "experiments", json={"projectId": pid, "name": "Retained sibling"}
    )
    for current in (eid, sibling["id"]):
        artifacts.upsert_named_experiment_artifact(
            current, "config.txt", "config.txt", b"config", "text/plain", "config"
        )
        call(
            api,
            "POST",
            f"scalars/log/{current}",
            json={"step": 1, "scalars": {"loss": 0.5}},
        )
    for category in ("experimentArtifacts", "scalars"):
        outcome = call(api, "POST", f"experiments/{eid}/cleanup/{category}")
        assert outcome["success"] and not outcome["errors"], outcome
    assert call(api, "GET", f"experiments/{eid}")["id"] == eid
    assert call(api, "GET", f"experiment-artifacts/experiments/{eid}")["total"] == 0
    assert (
        artifacts.download_named_experiment_artifact(
            sibling["id"], "config.txt"
        ).content
        == b"config"
    )
    eventually(
        lambda: call(api, "GET", f"scalars/get/{eid}"),
        lambda data: all(not row["scalars"] for row in data["data"]),
    )
    assert call(api, "GET", f"scalars/get/{sibling['id']}")["data"][0]["scalars"][
        "loss"
    ]["y"] == [0.5]


def test_full_deletion_removes_satellite_data(
    api, project, experiment, artifacts, storage, scalars
):
    """Delete experiment satellite data, then remove project blobs and scalar tables."""
    pid, eid = project["id"], experiment["id"]
    artifacts.upsert_named_experiment_artifact(
        eid, "config.txt", "config.txt", b"configuration", "text/plain", "config"
    )
    row = call(api, "GET", f"experiment-artifacts/experiments/{eid}")["data"][0]
    digest = row["storagePath"]
    shared = artifacts.upload_project_artifact(
        pid, "data.bin", b"project data", "application/octet-stream"
    )
    call(api, "POST", f"scalars/log/{eid}", json={"step": 1, "scalars": {"loss": 1.0}})
    storage_path = (
        f"experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts/{digest}"
    )
    assert storage.get(storage_path).status_code == 200
    outcome = call(api, "DELETE", f"experiments/{eid}", params={"detailed": True})
    assert outcome["success"] and not outcome["errors"], outcome
    metadata_path = (
        f"experiment-artifacts/projects/{pid}/experiments/{eid}/artifacts/info"
    )
    assert (
        storage.get(metadata_path, params={"file_path": "config.txt"}).status_code
        == 404
    )
    assert (
        call(storage, "GET", f"project-artifacts/{pid}/usage")["experimentBuckets"][
            "count"
        ]
        == 0
    )
    eventually(
        lambda: call(scalars, "GET", f"projects/experiments/{pid}"),
        lambda data: eid not in str(data),
    )
    response = api.get(f"project-artifacts/{pid}/artifacts/{shared.hash}")
    assert response.status_code == 200 and response.content == b"project data"
    outcome = call(api, "DELETE", f"projects/{pid}", params={"detailed": True})
    assert outcome["success"] and not outcome["errors"], outcome
    assert (
        call(storage, "GET", f"project-artifacts/{pid}/usage")["projectArtifacts"][
            "count"
        ]
        == 0
    )
    usage = call(scalars, "GET", f"projects/{pid}/usage")
    assert all(not table["exists"] for table in usage["tables"])


def test_missing_experiment_blob_returns_not_found(storage, project, experiment):
    """Return 404 for a missing experiment blob in the object-storage service."""
    response = storage.get(
        f"experiment-artifacts/projects/{project['id']}/experiments/{experiment['id']}/artifacts/{'0' * 32}"
    )
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "category", ["projectArtifacts", "snapshots", "experimentBuckets", "scalars"]
)
def test_project_category_cleanup_preserves_project(
    api, project, experiment, artifacts, tracker, storage, scalars, tmp_path, category
):
    """Clear each selected storage category while retaining project and experiment rows."""
    pid, eid = project["id"], experiment["id"]
    if category == "projectArtifacts":
        artifacts.upload_project_artifact(
            pid, "data.bin", b"data", "application/octet-stream"
        )
    elif category == "snapshots":
        source = tmp_path / "train.py"
        source.write_text("epochs = 2\n")
        tracker.log_snapshot(source, root=tmp_path)
    elif category == "experimentBuckets":
        artifacts.upsert_named_experiment_artifact(
            eid, "config.txt", "config.txt", b"config", "text/plain"
        )
    else:
        call(
            api,
            "POST",
            f"scalars/log/{eid}",
            json={"step": 1, "scalars": {"loss": 1.0}},
        )
    outcome = call(api, "POST", f"projects/{pid}/cleanup/{category}")
    assert outcome["success"] and not outcome["errors"], outcome
    assert call(api, "GET", f"projects/{pid}")["id"] == pid
    assert call(api, "GET", f"experiments/{eid}")["id"] == eid
    if category == "scalars":
        assert all(
            not row["exists"]
            for row in call(scalars, "GET", f"projects/{pid}/usage")["tables"]
        )
    else:
        assert (
            call(storage, "GET", f"project-artifacts/{pid}/usage")[category]["count"]
            == 0
        )


@pytest.mark.parametrize(
    "kind", ["scalars", "named", "project", "snapshot", "metrics", "hparams"]
)
def test_foreign_user_cannot_read_training_data(
    api, project, experiment, artifacts, tracker, make_user, tmp_path, kind
):
    """Deny another user access to each category of private training data."""
    pid, eid = project["id"], experiment["id"]
    if kind == "scalars":
        call(
            api,
            "POST",
            f"scalars/log/{eid}",
            json={"step": 1, "scalars": {"private": 1.0}},
        )
        path, params = f"scalars/get/{eid}", {}
    elif kind == "named":
        artifacts.upsert_named_experiment_artifact(
            eid, "secret.txt", "secret.txt", b"secret", "text/plain"
        )
        path, params = (
            "experiment-artifacts/download",
            {"experiment_id": eid, "filepath": "secret.txt"},
        )
    elif kind == "project":
        result = artifacts.upload_project_artifact(
            pid, "data.bin", b"private data", "application/octet-stream"
        )
        path, params = f"project-artifacts/{pid}/artifacts/{result.hash}", {}
    elif kind == "snapshot":
        source = tmp_path / "private.py"
        source.write_text("secret = True\n")
        tracker.log_snapshot(source, root=tmp_path)
        path, params = f"experiments/{eid}/data/snapshot/files", {}
    elif kind == "metrics":
        call(
            api,
            "POST",
            "metrics",
            json={"experimentId": eid, "name": "private", "value": 1},
        )
        path, params = f"experiments/{eid}/metrics", {}
    else:
        tracker.log_hparams({"private": True})
        path, params = f"experiments/{eid}/hparams", {}
    response = make_user()["client"].get(path, params=params)
    assert response.status_code in (403, 404), response.text
