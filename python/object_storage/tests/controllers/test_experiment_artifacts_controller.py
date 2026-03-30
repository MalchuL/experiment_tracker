from __future__ import annotations

import re
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.db import get_async_session
from object_storage.db.models import Base
from object_storage.domain.experiment_artifacts_storage.controller import router
from object_storage.storage import get_storage
from object_storage.storage.s3_client import get_s3_storage


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
        params={"hash": artifact_hash},
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
async def test_experiment_controller_tracked_upload_list_download_delete(http_client) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"tracked-artifact-content"
    artifact_hash = "e" * 64
    artifact_path = "configs/train.yaml"

    upload = await http_client.post(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
        params={
            "hash": artifact_hash,
            "path": artifact_path,
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
    assert len(artifacts) == 1
    assert artifacts[0]["hash"] == artifact_hash
    assert artifacts[0]["file_path"] == artifact_path

    tracked_download = await http_client.get(
        f"/api/experiment-artifacts/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}",
        params={"tracked": "true"},
    )
    assert tracked_download.status_code == 200
    assert tracked_download.content == payload
    assert "attachment; filename=\"train.yaml\"" in tracked_download.headers.get(
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
    assert delete_experiment.json()["deleted_count"] == 0


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
        params={"path": artifact_path},
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
    assert len(artifacts) == 1
    assert artifacts[0]["hash"] == h
    assert artifacts[0]["file_path"] == artifact_path

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
