from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.db import get_async_session
from object_storage.db.models import Base, ExperimentBlob
from object_storage.domain.experiment_artifacts_storage.controller import router
from object_storage.storage import get_storage
from object_storage.storage.s3_client import get_s3_storage


def _maxish_file_path(index: int) -> str:
    """1024-char path (``ExperimentBlob.file_path`` max), unique per ``index``."""

    prefix = f"experiments/run_{index:05d}/checkpoints/"
    suffix = ".pt"
    pad_len = 1024 - len(prefix) - len(suffix)
    assert pad_len > 0
    return f"{prefix}{'p' * pad_len}{suffix}"


@pytest.fixture
async def db_session_factory(pytestconfig: pytest.Config):
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield factory
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def http_client(db_session_factory):
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def _override_session():
        async with db_session_factory() as session:
            yield session

    def _override_storage():
        return get_s3_storage()

    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_storage] = _override_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_experiment_controller_untracked_upload_and_download(http_client) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"untracked-artifact-content"
    artifact_hash = "d" * 64

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-untracked",
        params={"artifact_hash": artifact_hash},
        files={"file": ("artifact.bin", payload, "application/octet-stream")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["hash"] == artifact_hash
    assert body["size"] == len(payload)

    download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}"
    )
    assert download.status_code == 200
    assert download.content == payload


@pytest.mark.asyncio
async def test_experiment_controller_untracked_no_hash_response_key_matches_download(
    http_client,
) -> None:
    """Omitted hash query: JSON hash must be the object key used for download."""

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"no-hash-query-untracked"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-untracked",
        files={"file": ("blob.bin", payload, "application/octet-stream")},
    )
    assert upload.status_code == 200
    body = upload.json()
    h = body["hash"]
    assert re.fullmatch(r"[0-9a-f]{32}", h)
    assert body["size"] == len(payload)

    download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{h}"
    )
    assert download.status_code == 200
    assert download.content == payload


@pytest.mark.asyncio
async def test_experiment_controller_tracked_upload_list_download_delete(
    http_client,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"tracked-artifact-content"
    artifact_hash = "e" * 64
    artifact_path = "configs/train.yaml"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={
            "artifact_hash": artifact_hash,
            "file_path": artifact_path,
            "content_type": "application/x-yaml",
        },
        files={"file": ("train.yaml", payload, "application/x-yaml")},
    )
    assert upload.status_code == 200
    upload_body = upload.json()
    assert UUID(upload_body["id"])
    assert upload_body["hash"] == artifact_hash
    assert upload_body["file_path"] == artifact_path

    listed = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts"
    )
    assert listed.status_code == 200
    artifacts = listed.json()
    assert artifacts["size"] == 1
    assert artifacts["has_next"] is False
    assert artifacts["data"][0]["hash"] == artifact_hash
    assert artifacts["data"][0]["file_path"] == artifact_path

    tracked_download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}",
        params={"tracked": "true"},
    )
    assert tracked_download.status_code == 200
    assert tracked_download.content == payload
    assert 'attachment; filename="train.yaml"' in tracked_download.headers.get(
        "content-disposition", ""
    )

    delete_artifact = await http_client.delete(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}"
    )
    assert delete_artifact.status_code == 200
    assert delete_artifact.json()["deleted"] is True

    delete_experiment = await http_client.delete(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}"
    )
    assert delete_experiment.status_code == 200
    assert delete_experiment.json()["deleted_count"] == -1


@pytest.mark.asyncio
async def test_experiment_controller_tracked_download_unicode_filename(
    http_client,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"mp4-bytes-placeholder"
    artifact_hash = "f" * 64
    display_name = "! Двач @dvachannel @rand2ch @ru2ch_ban ! (1).mp4"
    artifact_path = "final/!_Двач_@dvachannel_@rand2ch_@ru2ch_ban_!_(1).mp4"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={
            "artifact_hash": artifact_hash,
            "file_path": artifact_path,
            "content_type": "video/mp4",
        },
        files={"file": (display_name, payload, "video/mp4")},
    )
    assert upload.status_code == 200

    download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}",
        params={"tracked": "true"},
    )
    assert download.status_code == 200
    assert download.content == payload
    disposition = download.headers.get("content-disposition", "")
    assert disposition.startswith("attachment; filename*=UTF-8''")
    disposition.encode("latin-1")


@pytest.mark.asyncio
async def test_experiment_controller_tracked_no_hash_list_and_download_use_same_key(
    http_client,
) -> None:
    """Omitted hash query: list + download must use the same key as upload response."""

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"tracked-without-hash-param"
    artifact_path = "artifacts/run.bin"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={"file_path": artifact_path},
        files={"file": ("run.bin", payload, "application/octet-stream")},
    )
    assert upload.status_code == 200
    upload_body = upload.json()
    h = upload_body["hash"]
    assert re.fullmatch(r"[0-9a-f]{32}", h)
    assert upload_body["file_path"] == artifact_path
    assert upload_body["mime_type"] == "application/octet-stream"

    listed = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts"
    )
    assert listed.status_code == 200
    artifacts = listed.json()
    assert artifacts["size"] == 1
    assert artifacts["data"][0]["hash"] == h
    assert artifacts["data"][0]["file_path"] == artifact_path

    tracked_download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{h}",
        params={"tracked": "true"},
    )
    assert tracked_download.status_code == 200
    assert tracked_download.content == payload

    delete_experiment = await http_client.delete(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}"
    )
    assert delete_experiment.status_code == 200


@pytest.mark.asyncio
async def test_experiment_controller_tracked_upload_metadata_query_roundtrip(
    http_client,
) -> None:
    """``metadata`` query JSON is returned on upload and on list."""

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"meta-query-body"
    artifact_hash = "f" * 64
    artifact_path = "weights/model.pt"
    meta = {"name": "from-query", "epoch": 2, "tags": ["x"]}

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={
            "artifact_hash": artifact_hash,
            "file_path": artifact_path,
            "metadata": json.dumps(meta),
        },
        files={"file": ("model.pt", payload, "application/octet-stream")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["hash"] == artifact_hash
    assert body["file_path"] == artifact_path
    assert body["metadata"] == meta

    listed = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts"
    )
    assert listed.status_code == 200
    artifacts = listed.json()
    assert artifacts["size"] == 1
    assert artifacts["data"][0]["metadata"] == meta


@pytest.mark.asyncio
async def test_experiment_controller_tracked_list_applies_limit_offset(http_client) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    first_hash = "1" * 64
    second_hash = "2" * 64

    await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={"artifact_hash": first_hash, "file_path": "a.bin"},
        files={"file": ("a.bin", b"a", "application/octet-stream")},
    )
    await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={"artifact_hash": second_hash, "file_path": "b.bin"},
        files={"file": ("b.bin", b"b", "application/octet-stream")},
    )

    page0 = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts",
        params={"limit": 1, "offset": 0},
    )
    page1 = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts",
        params={"limit": 1, "offset": 1},
    )
    assert page0.status_code == 200
    assert page1.status_code == 200
    h0 = page0.json()["data"][0]["hash"]
    h1 = page1.json()["data"][0]["hash"]
    assert h0 != h1
    assert {h0, h1} == {first_hash, second_hash}
    assert page0.json()["total"] == 2
    assert page1.json()["total"] == 2


@pytest.mark.asyncio
async def test_experiment_controller_list_many_max_length_file_paths_via_query(
    http_client,
    db_session_factory,
) -> None:
    """httpx + Starlette/FastAPI must parse a long query string of ``file_path`` values."""

    project_id = uuid4()
    experiment_id = uuid4()
    n_rows = 20
    base_time = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    stored_paths: list[str] = []

    async with db_session_factory() as session:
        for i in range(n_rows):
            path = _maxish_file_path(i)
            assert len(path) == 1024
            stored_paths.append(path)
            session.add(
                ExperimentBlob(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    artifact_hash=f"{i:064d}",
                    file_path=path,
                    mime_type="application/octet-stream",
                    size=128 + i,
                    created_at=base_time + timedelta(milliseconds=i),
                    updated_at=base_time + timedelta(milliseconds=i),
                )
            )
        await session.commit()

    bogus_paths = [_maxish_file_path(90_000 + j) for j in range(6)]
    params: list[tuple[str, str | int]] = [
        ("file_path", p) for p in stored_paths + bogus_paths
    ]
    params.extend([("limit", 100), ("offset", 0)])

    url = (
        f"/api/experiment-artifacts/projects/{project_id}/experiments/"
        f"{experiment_id}/artifacts"
    )
    listed = await http_client.get(url, params=params)
    assert listed.status_code == 200, listed.text
    assert len(str(listed.url)) > 20_000

    body = listed.json()
    assert body["total"] == n_rows
    assert body["size"] == n_rows
    assert {row["file_path"] for row in body["data"]} == set(stored_paths)


@pytest.mark.asyncio
async def test_experiment_controller_get_tracked_artifact_info_by_hash(
    http_client,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    artifact_hash = "c" * 64
    artifact_path = "weights/model.bin"
    payload = b"model"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={"artifact_hash": artifact_hash, "file_path": artifact_path},
        files={"file": ("model.bin", payload, "application/octet-stream")},
    )
    assert upload.status_code == 200

    info = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/info",
        params={"artifact_hash": artifact_hash},
    )
    assert info.status_code == 200
    body = info.json()
    assert body["hash"] == artifact_hash
    assert body["file_path"] == artifact_path


@pytest.mark.asyncio
async def test_experiment_controller_tracked_upload_invalid_metadata_json_returns_400(
    http_client,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={
            "artifact_hash": "a" * 64,
            "file_path": "x.bin",
            "metadata": "not-json{",
        },
        files={"file": ("x.bin", b"x", "application/octet-stream")},
    )
    assert upload.status_code == 400
    assert upload.json()["detail"] == "metadata must be valid JSON"


@pytest.mark.asyncio
async def test_experiment_controller_tracked_upload_non_object_metadata_returns_400(
    http_client,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={"artifact_hash": "b" * 64, "file_path": "x.bin", "metadata": "[1,2,3]"},
        files={"file": ("x.bin", b"x", "application/octet-stream")},
    )
    assert upload.status_code == 400
    assert upload.json()["detail"] == "metadata must be a JSON object"
