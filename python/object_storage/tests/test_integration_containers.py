from __future__ import annotations

import hashlib
import io
import zipfile
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from object_storage.db.models import Base, TrackedBlob
from object_storage.domain.experiment_artifacts_storage.service import (
    ArtifactsStorageService,
)
from object_storage.domain.project_artifacts_storage.dto import (
    SnapshotCreateRequestDTO,
    SnapshotFileEntryDTO,
)
from object_storage.domain.project_artifacts_storage.repository import (
    ObjectStorageRepository,
)
from object_storage.domain.project_artifacts_storage.service import ObjectStorageService
from object_storage.storage.s3_client import get_s3_storage


def _read_stream(stream) -> bytes:
    """Read all bytes from a blob stream and release resources."""
    try:
        chunks = list(stream.stream(32 * 1024))
        return b"".join(chunks)
    finally:
        stream.close()
        stream.release_conn()


@pytest.mark.asyncio
async def test_project_artifacts_workflow_with_isolated_containers(
    pytestconfig: pytest.Config,
) -> None:
    """
    Verify DB + object storage flow against isolated testcontainers.

    This test validates that runtime env overrides are enough to fully run
    upload/check/snapshot/delete logic without touching local dev services.
    """

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    payload = b"blob-payload-from-testcontainers"
    blob_hash = hashlib.sha256(payload).hexdigest()

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        upload_result = await service.upload_project_blob(project_id, blob_hash, upload)
        assert upload_result.status == "ok"

        check_result = await service.check_project_blobs(project_id, [blob_hash])
        assert check_result.missing == []

        snapshot_result = await service.create_project_snapshot(
            SnapshotCreateRequestDTO(
                project_id=project_id,
                experiment_id=uuid4(),
                files=[SnapshotFileEntryDTO(path="artifact.bin", hash=blob_hash)],
            )
        )
        snapshot_id = UUID(snapshot_result.snapshot_id)

        with pytest.raises(HTTPException, match="referenced by a snapshot") as exc_info:
            await service.delete_project_blob(project_id, blob_hash)
        assert exc_info.value.status_code == 400

        deleted_blobs = await service.delete_project_snapshot(project_id, snapshot_id)
        assert deleted_blobs == [blob_hash]

        delete_result = await service.delete_project_blob(project_id, blob_hash)
        assert delete_result.deleted is False

    await engine.dispose()


@pytest.mark.asyncio
async def test_check_blobs_returns_missing_hashes(pytestconfig: pytest.Config) -> None:
    """Check returns missing hashes when some blobs are not yet uploaded."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    payload = b"present-blob-content"
    present_hash = hashlib.sha256(payload).hexdigest()
    missing_hash = "a" * 64

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        await service.upload_project_blob(project_id, present_hash, upload)

        check_result = await service.check_project_blobs(
            project_id, [present_hash, missing_hash]
        )
        assert check_result.missing == [missing_hash]

    await engine.dispose()


@pytest.mark.asyncio
async def test_download_blob_roundtrip(pytestconfig: pytest.Config) -> None:
    """Upload blob then download via get_blob_stream and verify content."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    payload = b"download-roundtrip-payload"
    blob_hash = hashlib.sha256(payload).hexdigest()

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        await service.upload_project_blob(project_id, blob_hash, upload)

        blob_stream = await service.get_project_blob_stream(project_id, blob_hash)
        downloaded = _read_stream(blob_stream)
        assert downloaded == payload

    await engine.dispose()


@pytest.mark.asyncio
async def test_snapshot_download_full_zip(pytestconfig: pytest.Config) -> None:
    """Create snapshot with all blobs present, download ZIP and verify contents."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    content_a = b"file-a-content"
    content_b = b"file-b-content"
    hash_a = hashlib.sha256(content_a).hexdigest()
    hash_b = hashlib.sha256(content_b).hexdigest()

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        for payload, h in [(content_a, hash_a), (content_b, hash_b)]:
            upload = UploadFile(filename="x.bin", file=io.BytesIO(payload))
            await service.upload_project_blob(project_id, h, upload)

        snapshot_result = await service.create_project_snapshot(
            SnapshotCreateRequestDTO(
                project_id=project_id,
                experiment_id=uuid4(),
                files=[
                    SnapshotFileEntryDTO(path="dir/a.bin", hash=hash_a),
                    SnapshotFileEntryDTO(path="dir/b.bin", hash=hash_b),
                ],
            )
        )
        snapshot_id = UUID(snapshot_result.snapshot_id)

        zip_path, _ = await service.prepare_project_snapshot_download(
            project_id, snapshot_id
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert set(zf.namelist()) == {"dir/a.bin", "dir/b.bin"}
            assert zf.read("dir/a.bin") == content_a
            assert zf.read("dir/b.bin") == content_b

    await engine.dispose()


@pytest.mark.asyncio
async def test_snapshot_download_with_missing_blobs(pytestconfig: pytest.Config) -> None:
    """Snapshot download includes __missing_blobs_manifest__.txt when blobs absent from S3."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    present_payload = b"present-content"
    present_hash = hashlib.sha256(present_payload).hexdigest()
    missing_hash = "b" * 64

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        service = ObjectStorageService(repository, storage)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(present_payload))
        await service.upload_project_blob(project_id, present_hash, upload)

        session.add(
            TrackedBlob(
                hash=missing_hash,
                project_id=project_id,
                size=10,
                ref_count=0,
            )
        )
        await session.commit()

        snapshot_result = await service.create_project_snapshot(
            SnapshotCreateRequestDTO(
                project_id=project_id,
                experiment_id=uuid4(),
                files=[
                    SnapshotFileEntryDTO(path="present.bin", hash=present_hash),
                    SnapshotFileEntryDTO(path="missing.bin", hash=missing_hash),
                ],
            )
        )
        snapshot_id = UUID(snapshot_result.snapshot_id)

        zip_path, _ = await service.prepare_project_snapshot_download(
            project_id, snapshot_id
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert set(zf.namelist()) == {"present.bin", "__missing_blobs_manifest__.txt"}
            assert zf.read("present.bin") == present_payload
            manifest = zf.read("__missing_blobs_manifest__.txt").decode("utf-8")
            assert f"missing.bin: {missing_hash}" in manifest

    await engine.dispose()


@pytest.mark.asyncio
async def test_experiment_artifacts_workflow(pytestconfig: pytest.Config) -> None:
    """Upload, download, delete artifact and delete experiment against real S3."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    storage = get_s3_storage()
    service = ArtifactsStorageService(storage)

    experiment_id = uuid4()
    payload = b"experiment-artifact-content"
    upload = UploadFile(filename="weights.bin", file=io.BytesIO(payload))

    upload_result = await service.upload_artifact(experiment_id, upload)
    assert upload_result.status == "ok"
    assert upload_result.size == len(payload)
    assert len(upload_result.path) == 32

    stream = await service.get_artifact_stream(experiment_id, upload_result.path)
    downloaded = _read_stream(stream)
    assert downloaded == payload

    delete_result = await service.delete_artifact(
        experiment_id, upload_result.path
    )
    assert delete_result.deleted is True

    exp_delete = await service.delete_experiment(experiment_id)
    assert exp_delete.deleted_count >= 1
