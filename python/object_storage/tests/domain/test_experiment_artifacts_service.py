from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi import UploadFile
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


class FakeBucketsService:
    def __init__(self) -> None:
        self.ensure_bucket_calls: list[tuple[str, str]] = []
        self.upload_blob_calls: list[tuple[str, str, str]] = []
        self.get_blob_stream_calls: list[tuple[str, str, str]] = []
        self.delete_blob_calls: list[tuple[str, str, str]] = []
        self.delete_bucket_calls: list[tuple[str, str]] = []
        self.committed = False
        self.upload_result = UploadBlobResult(size=0, hash="")
        self.stream = FakeBlobStream()

    async def ensure_bucket(self, project_id, experiment_id) -> str:
        self.ensure_bucket_calls.append((str(project_id), str(experiment_id)))
        return "bucket"

    async def upload_blob(self, project_id, experiment_id, upload, hash):
        self.upload_blob_calls.append((str(project_id), str(experiment_id), hash))
        self.upload_result = UploadBlobResult(size=len(await upload.read()), hash=hash)
        return self.upload_result

    async def get_blob_stream(self, project_id, experiment_id, hash):
        self.get_blob_stream_calls.append((str(project_id), str(experiment_id), hash))
        return self.stream

    async def delete_blob(self, project_id, experiment_id, hash) -> bool:
        self.delete_blob_calls.append((str(project_id), str(experiment_id), hash))
        return True

    async def delete_bucket(self, project_id, experiment_id) -> None:
        self.delete_bucket_calls.append((str(project_id), str(experiment_id)))

    async def commit(self) -> None:
        self.committed = True


class FakeArtifactsRepository:
    def __init__(self) -> None:
        self.commit_called = False
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
        self.commit_called = True


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
        hash="a" * 64,
        path="metrics/final.json",
    )

    assert result.hash == "a" * 64
    assert result.file_path == "metrics/final.json"
    assert len(repo.created) == 1
    assert repo.created[0].mime_type == "application/json"
    assert repo.commit_called is True


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
