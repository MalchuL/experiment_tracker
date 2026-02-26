from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi import UploadFile

from object_storage.domain.experiment_artifacts_storage.service import (
    ArtifactsStorageService,
)


class FakeStorage:
    def __init__(self) -> None:
        self.ensure_bucket_calls: list[str] = []
        self.put_blob_calls: list[tuple[str, str, int, bytes]] = []
        self.delete_bucket_result: int = 3

    def ensure_bucket(self, bucket_name: str) -> None:
        self.ensure_bucket_calls.append(bucket_name)

    def delete_bucket(self, bucket_name: str) -> int:
        return self.delete_bucket_result

    def stat_blob(self, bucket_name: str, blob_hash: str) -> bool:
        return False

    def put_blob(self, bucket_name: str, blob_hash: str, data, size: int) -> None:
        payload = data.read(size)
        self.put_blob_calls.append((bucket_name, blob_hash, size, payload))

    def get_blob(self, bucket_name: str, blob_hash: str):
        raise NotImplementedError

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_upload_artifact_stores_payload_with_generated_path() -> None:
    experiment_id = uuid4()
    storage = FakeStorage()
    service = ArtifactsStorageService(storage)
    payload = b"experiment-file-content"
    upload = UploadFile(filename="weights.bin", file=io.BytesIO(payload))

    result = await service.upload_artifact(experiment_id, upload)

    assert result.status == "ok"
    assert result.size == len(payload)
    assert len(result.path) == 32
    assert storage.ensure_bucket_calls == [f"experiment-{experiment_id}"]
    assert storage.put_blob_calls == [
        (f"experiment-{experiment_id}", result.path, len(payload), payload)
    ]


@pytest.mark.asyncio
async def test_delete_experiment_returns_deleted_count() -> None:
    experiment_id = uuid4()
    storage = FakeStorage()
    storage.delete_bucket_result = 5
    service = ArtifactsStorageService(storage)

    result = await service.delete_experiment(experiment_id)

    assert result.deleted_count == 5
