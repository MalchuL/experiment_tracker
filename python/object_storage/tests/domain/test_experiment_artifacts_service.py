from __future__ import annotations

import io
import re
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import Headers

from object_storage.db.models import ExperimentBlob
from object_storage.domain.buckets.dto import UploadBlobResult
from object_storage.domain.experiment_artifacts_storage.service import (
    ArtifactsStorageService,
)


class FakeBlobStream:
    def __init__(self) -> None:
        self.payload = b"artifact-bytes"

    def stream(self, chunk_size: int):
        _ = chunk_size
        yield self.payload

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class _FakeObjectStorage:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, str]] = []

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        self.deleted.append((bucket_name, blob_hash))
        return True


class FakeBucketsService:
    def __init__(self, *, commit_raises: bool = False) -> None:
        self.storage = _FakeObjectStorage()
        self.ensure_bucket_calls: list[tuple[str, str]] = []
        self.upload_blob_calls: list[tuple[str, str, str]] = []
        self.get_blob_stream_calls: list[tuple[str, str, str]] = []
        self.delete_blob_calls: list[tuple[str, str, str]] = []
        self.delete_bucket_calls: list[tuple[str, str]] = []
        self.committed = False
        self.rollback_called = False
        self._commit_raises = commit_raises
        self.upload_result = UploadBlobResult(size=0, hash="")
        self.stream = FakeBlobStream()

    async def ensure_bucket(self, project_id, experiment_id) -> str:
        self.ensure_bucket_calls.append((str(project_id), str(experiment_id)))
        return "bucket"

    async def upload_blob(self, project_id, experiment_id, upload, artifact_hash):
        self.upload_blob_calls.append((str(project_id), str(experiment_id), artifact_hash))
        self.upload_result = UploadBlobResult(
            size=len(await upload.read()), hash=artifact_hash
        )
        return self.upload_result

    async def get_blob_stream(self, project_id, experiment_id, artifact_hash):
        self.get_blob_stream_calls.append(
            (str(project_id), str(experiment_id), artifact_hash)
        )
        return self.stream

    async def delete_blob(self, project_id, experiment_id, artifact_hash) -> bool:
        self.delete_blob_calls.append(
            (str(project_id), str(experiment_id), artifact_hash)
        )
        return True

    async def delete_bucket(self, project_id, experiment_id) -> None:
        self.delete_bucket_calls.append((str(project_id), str(experiment_id)))

    async def commit(self) -> None:
        if self._commit_raises:
            raise RuntimeError("simulated commit failure")
        self.committed = True

    async def rollback(self) -> None:
        self.rollback_called = True


class FakeArtifactsRepository:
    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False
        self.fail_commit_with_integrity = False
        self.created: list[ExperimentBlob] = []
        self.list_result: list[ExperimentBlob] = []
        self.get_result: ExperimentBlob | None = None
        self.delete_blob_calls: list[tuple[str, str, str]] = []
        self.delete_all_calls: list[tuple[str, str]] = []

    async def create_experiment_blob(self, experiment_blob: ExperimentBlob) -> ExperimentBlob:
        if experiment_blob.id is None:
            experiment_blob.id = uuid4()
        self.created.append(experiment_blob)
        return experiment_blob

    async def list_experiment_blobs(
        self, project_id, experiment_id, limit=100, offset=0
    ) -> list[ExperimentBlob]:
        _ = (project_id, experiment_id, limit, offset)
        return self.list_result

    async def get_experiment_blob(self, project_id, experiment_id, artifact_hash):
        _ = (project_id, experiment_id, artifact_hash)
        return self.get_result

    async def delete_experiment_blob(self, project_id, experiment_id, artifact_hash) -> bool:
        self.delete_blob_calls.append(
            (str(project_id), str(experiment_id), artifact_hash)
        )
        return True

    async def delete_all_experiment_blobs(self, project_id, experiment_id) -> bool:
        self.delete_all_calls.append((str(project_id), str(experiment_id)))
        return True

    async def commit(self) -> None:
        if self.fail_commit_with_integrity:
            raise IntegrityError(None, None, Exception("simulated unique violation"))
        self.commit_called = True

    async def rollback(self) -> None:
        self.rollback_called = True


@pytest.mark.asyncio
async def test_upload_artifact_and_forget_stores_hash_and_size() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"experiment-file-content"
    upload = UploadFile(filename="weights.bin", file=io.BytesIO(payload))

    result = await service.upload_artifact_and_forget(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
    )

    assert result.hash
    assert result.size == len(payload)
    assert buckets_service.ensure_bucket_calls == [(str(project_id), str(experiment_id))]
    assert buckets_service.upload_blob_calls[0][0:2] == (
        str(project_id),
        str(experiment_id),
    )
    assert buckets_service.committed is True
    assert repo.created == []
    assert buckets_service.upload_blob_calls[0][2] == result.hash
    assert re.fullmatch(r"[0-9a-f]{32}", result.hash)


@pytest.mark.asyncio
async def test_upload_artifact_and_forget_explicit_hash_matches_upload_key() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"payload"
    explicit = "7" * 64
    upload = UploadFile(filename="f.bin", file=io.BytesIO(payload))

    result = await service.upload_artifact_and_forget(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        artifact_hash=explicit,
    )

    assert result.hash == explicit
    assert buckets_service.upload_blob_calls[0][2] == explicit


@pytest.mark.asyncio
async def test_upload_artifact_and_track_persists_experiment_blob() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"tracked-content"
    upload = UploadFile(
        filename="metrics.json",
        file=io.BytesIO(payload),
        headers=Headers({"content-type": "application/json"}),
    )

    result = await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        content_type="application/json",
        artifact_hash="a" * 64,
        file_path="metrics/final.json",
    )

    assert result.hash == "a" * 64
    assert result.file_path == "metrics/final.json"
    assert len(repo.created) == 1
    assert repo.created[0].artifact_hash == "a" * 64
    assert repo.created[0].mime_type == "application/json"
    assert repo.commit_called is True
    assert buckets_service.upload_blob_calls[0][2] == "a" * 64


@pytest.mark.asyncio
async def test_upload_tracked_persists_metadata_and_returns_in_dto() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"x"
    upload = UploadFile(
        filename="out.pt",
        file=io.BytesIO(payload),
        headers=Headers({"content-type": "application/octet-stream"}),
    )
    meta = {"name": "run-a", "epoch": 3, "tags": ["train"]}

    result = await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        artifact_hash="a" * 64,
        file_path="weights/out.pt",
        metadata=meta,
    )

    assert result.metadata == meta
    assert len(repo.created) == 1
    assert repo.created[0].artifact_metadata == meta


@pytest.mark.asyncio
async def test_upload_tracked_without_metadata_stores_empty_dict() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    upload = UploadFile(
        filename="only.bin",
        file=io.BytesIO(b"x"),
        headers=Headers({"content-type": "application/octet-stream"}),
    )

    result = await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        artifact_hash="d" * 64,
        file_path="dir/only.bin",
    )

    assert result.metadata == {}
    assert repo.created[0].artifact_metadata == {}


@pytest.mark.asyncio
async def test_list_artifacts_includes_metadata_in_response() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    blob_id = uuid4()
    meta = {"name": "listed", "version": 2}
    repo = FakeArtifactsRepository()
    repo.list_result = [
        ExperimentBlob(
            id=blob_id,
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_hash="f" * 64,
            file_path="group/file.bin",
            mime_type="application/octet-stream",
            size=99,
            artifact_metadata=meta,
        )
    ]
    buckets_service = FakeBucketsService()
    service = ArtifactsStorageService(buckets_service, repo)

    out = await service.list_artifacts(project_id, experiment_id)

    assert len(out) == 1
    assert out[0].metadata == meta
    assert out[0].hash == "f" * 64
    assert out[0].file_path == "group/file.bin"


@pytest.mark.asyncio
async def test_upload_tracked_uses_content_type_argument_not_upload_header() -> None:
    """Stored MIME type comes from ``content_type``, not from UploadFile headers."""

    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    upload = UploadFile(
        filename="x.json",
        file=io.BytesIO(b"{}"),
        headers=Headers({"content-type": "text/plain"}),
    )

    await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        content_type="application/json",
        artifact_hash="c" * 64,
        file_path="cfg/x.json",
    )

    assert repo.created[0].mime_type == "application/json"


@pytest.mark.asyncio
async def test_upload_tracked_uses_upload_content_type_when_param_omitted() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    upload = UploadFile(
        filename="x.json",
        file=io.BytesIO(b"{}"),
        headers=Headers({"content-type": "text/plain"}),
    )

    await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        artifact_hash="c" * 64,
        file_path="cfg/x.json",
    )

    assert repo.created[0].mime_type == "text/plain"


@pytest.mark.asyncio
async def test_upload_artifact_and_track_without_hash_aligns_db_blob_and_upload_key() -> (
    None
):
    """Omitted hash: response, experiment_blobs.artifact_hash, and upload_blob key match."""

    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    upload = UploadFile(
        filename="x.bin",
        file=io.BytesIO(b"blob"),
        headers=Headers({"content-type": "application/octet-stream"}),
    )

    result = await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=upload,
        content_type="application/octet-stream",
        file_path="dir/x.bin",
    )

    h = result.hash
    assert re.fullmatch(r"[0-9a-f]{32}", h)
    assert buckets_service.upload_blob_calls[0][2] == h
    assert len(repo.created) == 1
    assert repo.created[0].artifact_hash == h


@pytest.mark.asyncio
async def test_get_artifact_stream_returns_tracked_metadata() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    repo = FakeArtifactsRepository()
    repo.get_result = ExperimentBlob(
        project_id=project_id,
        experiment_id=experiment_id,
        artifact_hash="b" * 64,
        file_path="runs/model.bin",
        mime_type="application/octet-stream",
        size=123,
    )
    buckets_service = FakeBucketsService()
    service = ArtifactsStorageService(buckets_service, repo)

    result = await service.get_artifact_stream(
        project_id=project_id,
        experiment_id=experiment_id,
        artifact_hash="b" * 64,
        tracked=True,
    )

    assert result.file_path == "runs/model.bin"
    assert result.filename == "model.bin"
    assert result.size == 123


@pytest.mark.asyncio
async def test_delete_experiment_deletes_bucket_and_metadata() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)

    result = await service.delete_experiment(project_id, experiment_id)

    assert buckets_service.delete_bucket_calls == [(str(project_id), str(experiment_id))]
    assert repo.delete_all_calls == [(str(project_id), str(experiment_id))]
    assert repo.commit_called is True
    assert result.deleted_count == 0


@pytest.mark.asyncio
async def test_upload_tracked_invalid_path_rolls_back_and_removes_s3_object() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"tracked-content"
    upload = UploadFile(
        filename="metrics.json",
        file=io.BytesIO(payload),
        headers=Headers({"content-type": "application/json"}),
    )
    bad_path = "../outside.json"

    with pytest.raises(ValueError, match="Invalid file path"):
        await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            content_type="application/json",
            artifact_hash="a" * 64,
            file_path=bad_path,
        )

    assert repo.rollback_called is True
    assert repo.commit_called is False
    assert repo.created == []
    assert buckets_service.storage.deleted == [("bucket", "a" * 64)]


@pytest.mark.asyncio
async def test_upload_tracked_integrity_error_rolls_back_and_removes_s3_object() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService()
    repo = FakeArtifactsRepository()
    repo.fail_commit_with_integrity = True
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"tracked-content"
    upload = UploadFile(
        filename="metrics.json",
        file=io.BytesIO(payload),
        headers=Headers({"content-type": "application/json"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.upload_artifact_and_track(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            content_type="application/json",
            artifact_hash="b" * 64,
            file_path="metrics/final.json",
        )

    assert exc_info.value.status_code == 500
    assert repo.rollback_called is True
    assert buckets_service.storage.deleted == [("bucket", "b" * 64)]


@pytest.mark.asyncio
async def test_upload_untracked_commit_failure_rolls_back_and_removes_s3_object() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    buckets_service = FakeBucketsService(commit_raises=True)
    repo = FakeArtifactsRepository()
    service = ArtifactsStorageService(buckets_service, repo)
    payload = b"raw-bytes"
    upload = UploadFile(filename="blob.bin", file=io.BytesIO(payload))
    artifact_hash = "c" * 64

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        await service.upload_artifact_and_forget(
            project_id=project_id,
            experiment_id=experiment_id,
            upload=upload,
            artifact_hash=artifact_hash,
        )

    assert buckets_service.rollback_called is True
    assert buckets_service.committed is False
    assert buckets_service.storage.deleted == [("bucket", artifact_hash)]
