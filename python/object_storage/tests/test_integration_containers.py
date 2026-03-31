from __future__ import annotations

import hashlib
import io
import re
import zipfile
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import Headers

from object_storage.db.models import Base, ExperimentBlob, ProjectBlob
from object_storage.domain.buckets.repository import BucketsRepository
from object_storage.domain.buckets.service import (
    BucketRegistryService,
    project_experiment_bucket_name,
)
from object_storage.domain.experiment_artifacts_storage.repository import (
    ExperimentArtifactsRepository,
)
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


def _read_object_store_bytes(storage, bucket_name: str, blob_hash: str) -> bytes:
    """Load blob bytes from S3/MinIO by the hash key used for the object."""

    handle = storage.get_blob(bucket_name, blob_hash)
    return _read_stream(handle)


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
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

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
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

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
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        await service.upload_project_blob(project_id, blob_hash, upload)

        blob_stream = await service.get_project_blob_stream(project_id, blob_hash)
        downloaded = _read_stream(blob_stream)
        assert downloaded == payload

    await engine.dispose()


@pytest.mark.asyncio
async def test_project_blob_hash_case_insensitive_check_and_download(
    pytestconfig: pytest.Config,
) -> None:
    """CAS keys and DB rows use lowercase hex; API accepts any hex case consistently."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    payload = b"case-mix-payload"
    blob_hash_lower = hashlib.sha256(payload).hexdigest()
    blob_hash_upload = "".join(
        c.upper() if i % 3 == 0 else c for i, c in enumerate(blob_hash_lower)
    )
    blob_hash_check = "".join(
        c.upper() if i % 5 == 0 else c for i, c in enumerate(blob_hash_lower)
    )
    blob_hash_download = blob_hash_lower.swapcase()

    async with session_factory() as session:
        repository = ObjectStorageRepository(session)
        storage = get_s3_storage()
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
        upload_result = await service.upload_project_blob(
            project_id, blob_hash_upload, upload
        )
        assert upload_result.status == "ok"

        check_result = await service.check_project_blobs(
            project_id, [blob_hash_check, blob_hash_lower]
        )
        assert check_result.missing == []

        blob_stream = await service.get_project_blob_stream(
            project_id, blob_hash_download
        )
        assert _read_stream(blob_stream) == payload

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
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

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
        buckets = BucketRegistryService(BucketsRepository(session), storage)
        service = ObjectStorageService(repository, buckets)

        upload = UploadFile(filename="blob.bin", file=io.BytesIO(present_payload))
        await service.upload_project_blob(project_id, present_hash, upload)

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
    """Upload tracked and untracked experiment artifacts against real S3 + DB."""
    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    tracked_payload = b"experiment-tracked-content"
    untracked_payload = b"experiment-untracked-content"
    tracked_hash = "d" * 64
    untracked_hash = "e" * 64

    async with session_factory() as session:
        storage = get_s3_storage()
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)

        tracked_upload = UploadFile(
            filename="weights.bin",
            file=io.BytesIO(tracked_payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        tracked_result = await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=tracked_upload,
            hash=tracked_hash,
            file_path="weights/final.bin",
        )
        assert tracked_result.hash == tracked_hash
        assert tracked_result.size == len(tracked_payload)

        untracked_upload = UploadFile(
            filename="sample.png",
            file=io.BytesIO(untracked_payload),
            headers=Headers({"content-type": "image/png"}),
        )
        untracked_result = await service.upload_artifact_and_forget(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=untracked_upload,
            hash=untracked_hash,
        )
        assert untracked_result.hash == untracked_hash
        assert untracked_result.size == len(untracked_payload)

        tracked_stream = await service.get_artifact_stream(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_hash=tracked_hash,
            tracked=True,
        )
        tracked_downloaded = _read_stream(tracked_stream.stream)
        assert tracked_downloaded == tracked_payload

        untracked_stream = await service.get_artifact_stream(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_hash=untracked_hash,
            tracked=False,
        )
        untracked_downloaded = _read_stream(untracked_stream.stream)
        assert untracked_downloaded == untracked_payload

        delete_result = await service.delete_artifact(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_hash=tracked_hash,
        )
        assert delete_result.deleted is True

        exp_delete = await service.delete_experiment(project_id, experiment_id)
        assert exp_delete.deleted_count == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_tracked_upload_explicit_hash_db_row_and_object_store_key_match(
    pytestconfig: pytest.Config,
) -> None:
    """Passed hash must equal experiment_blobs.artifact_hash and the S3 object key."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"explicit-hash-tracked-payload"
    explicit_hash = "9" * 64
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="model.pt",
            file=io.BytesIO(payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        result = await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            content_type="application/octet-stream",
            hash=explicit_hash,
            file_path="weights/model.pt",
        )

    assert result.hash == explicit_hash

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == explicit_hash,
            )
        )
        blob = row.scalar_one()
        assert blob.artifact_hash == explicit_hash
        assert blob.file_path == "weights/model.pt"
        assert blob.mime_type == "application/octet-stream"

    assert storage.exists_blob(bucket_name, explicit_hash) is True
    assert _read_object_store_bytes(storage, bucket_name, explicit_hash) == payload

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        await service.delete_experiment(project_id, experiment_id)

    await engine.dispose()


@pytest.mark.asyncio
async def test_tracked_upload_metadata_roundtrip_in_database(
    pytestconfig: pytest.Config,
) -> None:
    """JSON metadata is stored on ``experiment_blobs.metadata`` and returned on upload."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"meta-payload-bytes"
    blob_hash = "5" * 64
    meta = {"name": "integration-blob", "epoch": 7, "tags": ["a", "b"]}

    async with session_factory() as session:
        storage = get_s3_storage()
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="w.pt",
            file=io.BytesIO(payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        result = await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            hash=blob_hash,
            file_path="artifacts/w.pt",
            metadata=meta,
        )

    assert result.metadata == meta

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == blob_hash,
            )
        )
        blob = row.scalar_one()
        assert blob.artifact_metadata == meta

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), get_s3_storage())
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        await service.delete_experiment(project_id, experiment_id)

    await engine.dispose()


@pytest.mark.asyncio
async def test_tracked_upload_omitted_hash_db_row_object_store_and_response_align(
    pytestconfig: pytest.Config,
) -> None:
    """When hash is omitted, response hash, DB artifact_hash, and S3 key must be identical."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"auto-id-tracked-payload"
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="data.bin",
            file=io.BytesIO(payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        result = await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            content_type="text/plain",
            file_path="data/file.bin",
        )

    h = result.hash
    assert re.fullmatch(r"[0-9a-f]{32}", h), "expected uuid4().hex-style id from service"
    assert result.size == len(payload)

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == h,
            )
        )
        blob = row.scalar_one()
        assert blob.artifact_hash == h
        assert blob.mime_type == "text/plain"

    assert storage.exists_blob(bucket_name, h) is True
    assert _read_object_store_bytes(storage, bucket_name, h) == payload

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        await service.delete_experiment(project_id, experiment_id)

    await engine.dispose()


@pytest.mark.asyncio
async def test_untracked_upload_explicit_hash_object_store_key_matches_response(
    pytestconfig: pytest.Config,
) -> None:
    """Passed hash must match response and the S3 object key (no experiment_blobs row)."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"untracked-explicit-hash"
    explicit_hash = "8" * 64
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="tmp.bin",
            file=io.BytesIO(payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        result = await service.upload_artifact_and_forget(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            hash=explicit_hash,
        )

    assert result.hash == explicit_hash
    assert storage.exists_blob(bucket_name, explicit_hash) is True
    assert _read_object_store_bytes(storage, bucket_name, explicit_hash) == payload

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == explicit_hash,
            )
        )
        assert row.scalar_one_or_none() is None

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        await service.delete_experiment(project_id, experiment_id)

    await engine.dispose()


@pytest.mark.asyncio
async def test_untracked_upload_omitted_hash_response_matches_object_store_key(
    pytestconfig: pytest.Config,
) -> None:
    """When hash is omitted, response hash must be the S3 object key (no DB experiment row)."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    payload = b"untracked-auto-id"
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="chunk.bin",
            file=io.BytesIO(payload),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        result = await service.upload_artifact_and_forget(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
        )

    h = result.hash
    assert re.fullmatch(r"[0-9a-f]{32}", h)
    assert result.size == len(payload)
    assert storage.exists_blob(bucket_name, h) is True
    assert _read_object_store_bytes(storage, bucket_name, h) == payload

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
        )
        assert row.scalars().first() is None

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        await service.delete_experiment(project_id, experiment_id)

    await engine.dispose()


async def _commit_raises_integrity_error(
    self: ExperimentArtifactsRepository,
) -> None:
    raise IntegrityError(None, None, Exception("simulated commit failure"))


@pytest.mark.asyncio
async def test_tracked_upload_invalid_path_leaves_db_and_object_store_clean(
    pytestconfig: pytest.Config,
) -> None:
    """After blob is written to S3, invalid path must rollback DB and remove the object."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    artifact_hash = "f" * 64
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    async with session_factory() as session:
        buckets_service = BucketRegistryService(BucketsRepository(session), storage)
        artifacts_repository = ExperimentArtifactsRepository(session)
        service = ArtifactsStorageService(buckets_service, artifacts_repository)
        upload = UploadFile(
            filename="x.bin",
            file=io.BytesIO(b"payload-for-invalid-path"),
            headers=Headers({"content-type": "application/octet-stream"}),
        )
        with pytest.raises(ValueError, match="Invalid file path"):
            await service.upload_artifact_and_track(
                project_id=project_id,
                experiment_id=experiment_id,
                upload=upload,
                content_type="application/octet-stream",
                hash=artifact_hash,
                file_path="../outside.bin",
            )

    async with session_factory() as read_session:
        row = await read_session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == artifact_hash,
            )
        )
        assert row.scalar_one_or_none() is None

    assert storage.exists_blob(bucket_name, artifact_hash) is False

    await engine.dispose()


@pytest.mark.asyncio
async def test_tracked_upload_commit_failure_leaves_db_and_object_store_clean(
    pytestconfig: pytest.Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If metadata commit fails, DB must stay unchanged and the uploaded object removed."""

    database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    assert database_url
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    project_id = uuid4()
    experiment_id = uuid4()
    artifact_hash = "1" * 64
    bucket_name = project_experiment_bucket_name(project_id, experiment_id)
    storage = get_s3_storage()

    monkeypatch.setattr(
        ExperimentArtifactsRepository,
        "commit",
        _commit_raises_integrity_error,
    )

    try:
        async with session_factory() as session:
            buckets_service = BucketRegistryService(BucketsRepository(session), storage)
            artifacts_repository = ExperimentArtifactsRepository(session)
            service = ArtifactsStorageService(buckets_service, artifacts_repository)
            upload = UploadFile(
                filename="ok.bin",
                file=io.BytesIO(b"commit-fail-payload"),
                headers=Headers({"content-type": "application/octet-stream"}),
            )
            with pytest.raises(HTTPException) as exc_info:
                await service.upload_artifact_and_track(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    upload=upload,
                    content_type="application/octet-stream",
                    hash=artifact_hash,
                    file_path="safe/relative/path.bin",
                )
            assert exc_info.value.status_code == 500

        async with session_factory() as read_session:
            row = await read_session.execute(
                select(ExperimentBlob).where(
                    ExperimentBlob.project_id == project_id,
                    ExperimentBlob.experiment_id == experiment_id,
                    ExperimentBlob.artifact_hash == artifact_hash,
                )
            )
            assert row.scalar_one_or_none() is None

        assert storage.exists_blob(bucket_name, artifact_hash) is False
    finally:
        monkeypatch.undo()
        await engine.dispose()
