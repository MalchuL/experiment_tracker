from __future__ import annotations

import hashlib
import io
import zipfile
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.db import get_async_session
from object_storage.db.models import Base, ProjectBlob, Snapshot
from object_storage.domain.project_artifacts_storage.controller import router
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
async def test_controller_upload_create_snapshot_and_deletion_errors(http_client) -> None:
    project_id = uuid4()
    payload = b"controller-test-payload"
    blob_hash = hashlib.sha256(payload).hexdigest()

    upload_response = await http_client.post(
        f"/api/project-artifacts/{project_id}/upload",
        params={"hash": blob_hash},
        files={"file": ("blob.bin", payload, "application/octet-stream")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["status"] == "ok"

    duplicate_upload = await http_client.post(
        f"/api/project-artifacts/{project_id}/upload",
        params={"hash": blob_hash},
        files={"file": ("blob.bin", payload, "application/octet-stream")},
    )
    assert duplicate_upload.status_code == 200
    assert duplicate_upload.json()["status"] == "exists"

    create_snapshot = await http_client.post(
        f"/api/project-artifacts/{project_id}/snapshots",
        json={
            "project_id": str(project_id),
            "experiment_id": str(uuid4()),
            "files": [{"path": "artifact.bin", "hash": blob_hash}],
        },
    )
    assert create_snapshot.status_code == 200

    delete_response = await http_client.delete(
        f"/api/project-artifacts/{project_id}/artifacts/{blob_hash}"
    )
    assert delete_response.status_code == 400
    assert "referenced by a snapshot" in delete_response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_path", ["bad:name.txt", "bad\nname.txt", "bad\tname.txt"])
async def test_controller_create_snapshot_rejects_special_symbol_paths(
    http_client, invalid_path: str
) -> None:
    project_id = uuid4()
    response = await http_client.post(
        f"/api/project-artifacts/{project_id}/snapshots",
        json={
            "project_id": str(project_id),
            "experiment_id": str(uuid4()),
            "files": [{"path": invalid_path, "hash": "f" * 64}],
        },
    )

    assert response.status_code == 400
    assert "Invalid path" in response.json()["detail"]


@pytest.mark.asyncio
async def test_controller_download_snapshot_contains_missing_manifest(
    http_client, db_session_factory
) -> None:
    project_id = uuid4()
    present_payload = b"present-content"
    present_hash = hashlib.sha256(present_payload).hexdigest()
    missing_hash = "b" * 64

    upload_response = await http_client.post(
        f"/api/project-artifacts/{project_id}/upload",
        params={"hash": present_hash},
        files={"file": ("blob.bin", present_payload, "application/octet-stream")},
    )
    assert upload_response.status_code == 200

    async with db_session_factory() as session:
        session.add(
            ProjectBlob(
                hash=missing_hash,
                project_id=project_id,
                mime_type="application/octet-stream",
                size=10,
                ref_count=0,
            )
        )
        await session.commit()

    create_snapshot = await http_client.post(
        f"/api/project-artifacts/{project_id}/snapshots",
        json={
            "project_id": str(project_id),
            "experiment_id": str(uuid4()),
            "files": [
                {"path": "present.bin", "hash": present_hash},
                {"path": "missing.bin", "hash": missing_hash},
            ],
        },
    )
    assert create_snapshot.status_code == 200
    snapshot_id = UUID(create_snapshot.json()["snapshot_id"])

    download_response = await http_client.get(
        f"/api/project-artifacts/{project_id}/snapshots/{snapshot_id}/download"
    )
    assert download_response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(download_response.content))
    assert set(archive.namelist()) == {"present.bin", "__missing_blobs_manifest__.txt"}
    assert archive.read("present.bin") == present_payload
    missing_manifest = archive.read("__missing_blobs_manifest__.txt").decode("utf-8")
    assert f"missing.bin: {missing_hash}" in missing_manifest


@pytest.mark.asyncio
async def test_controller_download_snapshot_rejects_invalid_manifest_path(
    http_client, db_session_factory
) -> None:
    project_id = uuid4()
    blob_hash = "c" * 64
    async with db_session_factory() as session:
        session.add(
            ProjectBlob(
                hash=blob_hash,
                project_id=project_id,
                mime_type="application/octet-stream",
                size=12,
                ref_count=0,
            )
        )
        snapshot = Snapshot(
            project_id=project_id,
            manifest=[
                {"path": "bad:path.txt", "hash": blob_hash},
            ]
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        snapshot_id = snapshot.id

    response = await http_client.get(
        f"/api/project-artifacts/{project_id}/snapshots/{snapshot_id}/download"
    )
    assert response.status_code == 400
    assert "Invalid path in snapshot" in response.json()["detail"]
