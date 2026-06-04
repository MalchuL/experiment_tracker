from __future__ import annotations

import hashlib
import io
import zipfile
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from object_storage.domain.buckets.dto import UploadBlobResult
from object_storage.domain.buckets.service import project_experiment_bucket_name
from object_storage.domain.project_artifacts_storage.dto import (
    SnapshotCreateRequestDTO,
    SnapshotFileEntryDTO,
)
from object_storage.domain.project_artifacts_storage.service import ObjectStorageService


class FakeStorage:
    def __init__(self) -> None:
        self.ensure_bucket_calls: list[str] = []
        self.put_blob_calls: list[tuple[str, str, int, bytes]] = []
        self.delete_blob_calls: list[tuple[str, str]] = []
        self.delete_bucket_calls: list[str] = []
        self.stat_blob_map: dict[tuple[str, str], bool] = {}
        self.object_payloads: dict[tuple[str, str], bytes] = {}

    def ensure_bucket(self, bucket_name: str) -> None:
        self.ensure_bucket_calls.append(bucket_name)

    def delete_bucket(self, bucket_name: str) -> bool:
        self.delete_bucket_calls.append(bucket_name)
        return True

    def exists_blob(self, bucket_name: str, blob_hash: str) -> bool:
        return self.stat_blob_map.get((bucket_name, blob_hash), False)

    def put_blob(self, bucket_name: str, blob_hash: str, data, size: int) -> None:
        payload = data.read(size)
        self.put_blob_calls.append((bucket_name, blob_hash, size, payload))

    def get_blob(self, bucket_name: str, blob_hash: str):
        payload = self.object_payloads.get((bucket_name, blob_hash), b"")

        class _Response:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def stream(self, _chunk_size: int):
                yield self._data

            def close(self) -> None:
                return None

            def release_conn(self) -> None:
                return None

        return _Response(payload)

    def delete_blob(self, bucket_name: str, blob_hash: str) -> bool:
        self.delete_blob_calls.append((bucket_name, blob_hash))
        return True


class FakeBucketsService:
    """Minimal async stand-in for BucketRegistryService in unit tests."""

    def __init__(self, storage: FakeStorage) -> None:
        self._storage = storage
        self.ensure_bucket_calls: list[tuple[object, object | None]] = []
        self.delete_all_project_buckets_calls: list[object] = []
        self.delete_blob_calls: list[tuple[object, object | None, str]] = []

    @property
    def storage(self) -> FakeStorage:
        return self._storage

    async def ensure_bucket(self, project_id, experiment_id) -> str:
        self.ensure_bucket_calls.append((project_id, experiment_id))
        name = project_experiment_bucket_name(project_id, experiment_id)
        self._storage.ensure_bucket(name)
        return name

    async def upload_blob(self, project_id, experiment_id, upload, hash) -> UploadBlobResult:
        name = project_experiment_bucket_name(project_id, experiment_id)
        body = await upload.read()
        self._storage.put_blob(name, hash, io.BytesIO(body), len(body))
        return UploadBlobResult(size=len(body), hash=hash)

    async def upload_blob_verifying_sha256(
        self,
        project_id,
        experiment_id,
        upload,
        expected_sha256_hex: str,
    ) -> UploadBlobResult:
        body = await upload.read()
        computed = hashlib.sha256(body).hexdigest()
        expected = expected_sha256_hex.strip().lower()
        if computed.lower() != expected:
            raise ValueError(
                f"Hash mismatch, computed: {computed}, expected: {expected_sha256_hex}"
            )
        name = project_experiment_bucket_name(project_id, experiment_id)
        self._storage.put_blob(name, expected, io.BytesIO(body), len(body))
        return UploadBlobResult(size=len(body), hash=expected)

    async def delete_blob(self, project_id, experiment_id, hash) -> bool:
        self.delete_blob_calls.append((project_id, experiment_id, hash))
        name = project_experiment_bucket_name(project_id, experiment_id)
        return self._storage.delete_blob(name, hash)

    async def delete_all_project_buckets(self, project_id) -> None:
        self.delete_all_project_buckets_calls.append(project_id)
        name = project_experiment_bucket_name(project_id, None)
        self._storage.delete_bucket(name)

    async def get_blob_stream(self, project_id, experiment_id, hash):
        name = project_experiment_bucket_name(project_id, experiment_id)
        return self._storage.get_blob(name, hash)


class FakeRepository:
    def __init__(self) -> None:
        self.existing_hashes: set[str] = set()
        self.blob_to_return = None
        self.add_blob_calls: list[tuple[str, int]] = []
        self.commit_calls = 0
        self.fetch_existing_calls = 0
        self.create_snapshot_calls = 0
        self.created_snapshot_manifest: list[dict] | None = None
        self.deleted_all_blobs_for = None
        self.deleted_all_snapshots_for = None
        self.snapshot_to_return = None
        self.decrement_blob_ref_calls: list[list[str]] = []
        self.delete_blob_calls: list[str] = []

    async def fetch_existing_blob_hashes(self, project_id, hashes):
        self.fetch_existing_calls += 1
        return {blob_hash for blob_hash in hashes if blob_hash in self.existing_hashes}

    async def fetch_blob(self, project_id, blob_hash):
        return self.blob_to_return

    async def add_blob(
        self, project_id, blob_hash: str, size: int, mime_type: str = "application/octet-stream"
    ) -> None:
        _ = mime_type
        self.add_blob_calls.append((blob_hash, size))

    async def create_snapshot(self, project_id, manifest: list[dict]):
        self.create_snapshot_calls += 1
        self.created_snapshot_manifest = manifest
        return SimpleNamespace(id=uuid4(), manifest=manifest)

    async def increment_blob_ref_counts(self, project_id, hashes) -> None:
        return None

    async def decrement_blob_ref_counts(self, project_id, hashes) -> None:
        self.decrement_blob_ref_calls.append(list(hashes))
        return None

    async def fetch_snapshot(self, snapshot_id):
        return self.snapshot_to_return

    async def delete_snapshot(self, snapshot_id):
        return True

    async def refresh(self, instance):
        return None

    async def rollback(self) -> None:
        return None

    async def delete_blob(self, project_id, blob_hash):
        self.delete_blob_calls.append(blob_hash)
        return True

    async def delete_all_blobs(self, project_id):
        self.deleted_all_blobs_for = project_id
        return None

    async def delete_all_snapshots(self, project_id):
        self.deleted_all_snapshots_for = project_id
        return None

    async def commit(self) -> None:
        self.commit_calls += 1


class FakeExperimentArtifactsRepository:
    def __init__(self) -> None:
        self.delete_all_experiment_blobs_calls: list[tuple[object, object]] = []

    async def delete_all_experiment_blobs(self, project_id, experiment_id) -> None:
        self.delete_all_experiment_blobs_calls.append((project_id, experiment_id))


@pytest.mark.asyncio
async def test_check_blobs_returns_only_missing_normalized_hashes() -> None:
    project_id = uuid4()
    existing_hash = "A" * 64
    missing_hash = "b" * 64
    repo = FakeRepository()
    repo.existing_hashes = {existing_hash.lower()}
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    result = await service.check_project_blobs(project_id, [existing_hash, missing_hash])

    assert result.missing == [missing_hash]
    assert buckets.ensure_bucket_calls == [(project_id, None)]
    assert storage.ensure_bucket_calls == [project_experiment_bucket_name(project_id, None)]


@pytest.mark.asyncio
async def test_upload_blob_rejects_hash_mismatch() -> None:
    project_id = uuid4()
    repo = FakeRepository()
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())
    upload = UploadFile(filename="artifact.bin", file=io.BytesIO(b"payload"))

    with pytest.raises(HTTPException, match="Hash mismatch") as exc_info:
        await service.upload_project_blob(project_id, "0" * 64, upload)

    assert exc_info.value.status_code == 400
    assert repo.add_blob_calls == []
    assert storage.put_blob_calls == []
    assert repo.commit_calls == 0


@pytest.mark.asyncio
async def test_create_snapshot_rejects_parent_traversal_paths() -> None:
    project_id = uuid4()
    payload = SnapshotCreateRequestDTO(
        project_id=project_id,
        experiment_id=uuid4(),
        files=[SnapshotFileEntryDTO(path="../secret.txt", hash="f" * 64)],
    )
    repo = FakeRepository()
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    with pytest.raises(HTTPException, match="Invalid path") as exc_info:
        await service.create_project_snapshot(payload)

    assert exc_info.value.status_code == 400
    assert repo.create_snapshot_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_path", ["bad:name.txt", "bad\nname.txt", "bad\tname.txt"])
async def test_create_snapshot_rejects_special_symbol_paths(invalid_path: str) -> None:
    project_id = uuid4()
    payload = SnapshotCreateRequestDTO(
        project_id=project_id,
        experiment_id=uuid4(),
        files=[SnapshotFileEntryDTO(path=invalid_path, hash="f" * 64)],
    )
    repo = FakeRepository()
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    with pytest.raises(HTTPException, match="Invalid path") as exc_info:
        await service.create_project_snapshot(payload)

    assert exc_info.value.status_code == 400
    assert repo.create_snapshot_calls == 0


@pytest.mark.asyncio
async def test_create_snapshot_stores_manifest_file_size_from_request() -> None:
    project_id = uuid4()
    blob_hash = "a" * 64
    payload = SnapshotCreateRequestDTO(
        project_id=project_id,
        experiment_id=uuid4(),
        files=[SnapshotFileEntryDTO(path="src/train.py", hash=blob_hash, size=12)],
    )
    repo = FakeRepository()
    repo.existing_hashes = {blob_hash}
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    await service.create_project_snapshot(payload)

    assert repo.created_snapshot_manifest == [
        {"path": "src/train.py", "hash": blob_hash, "size": 12}
    ]


@pytest.mark.asyncio
async def test_create_snapshot_accepts_manifest_size_different_from_stored_blob() -> None:
    project_id = uuid4()
    blob_hash = "a" * 64
    payload = SnapshotCreateRequestDTO(
        project_id=project_id,
        experiment_id=uuid4(),
        files=[SnapshotFileEntryDTO(path="src/train.py", hash=blob_hash, size=11)],
    )
    repo = FakeRepository()
    repo.existing_hashes = {blob_hash}
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    await service.create_project_snapshot(payload)

    assert repo.created_snapshot_manifest == [
        {"path": "src/train.py", "hash": blob_hash, "size": 11}
    ]


@pytest.mark.asyncio
async def test_get_snapshot_manifest_keeps_missing_legacy_manifest_size() -> None:
    project_id = uuid4()
    snapshot_id = uuid4()
    blob_hash = "a" * 64
    repo = FakeRepository()
    repo.snapshot_to_return = SimpleNamespace(
        id=snapshot_id,
        project_id=project_id,
        manifest=[{"path": "src/train.py", "hash": blob_hash}],
    )
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    result = await service.get_project_snapshot_manifest(project_id, snapshot_id)

    assert result.files[0].size is None


@pytest.mark.asyncio
async def test_delete_blob_rejects_referenced_blob() -> None:
    project_id = uuid4()
    blob_hash = "a" * 64
    repo = FakeRepository()
    repo.blob_to_return = SimpleNamespace(ref_count=1)
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    with pytest.raises(HTTPException, match="referenced by a snapshot") as exc_info:
        await service.delete_project_blob(project_id, blob_hash)

    assert exc_info.value.status_code == 400
    assert buckets.delete_blob_calls == []
    assert storage.delete_blob_calls == []


@pytest.mark.asyncio
async def test_delete_project_removes_bucket_and_metadata_rows() -> None:
    project_id = uuid4()
    repo = FakeRepository()
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    result = await service.delete_project(project_id)

    assert result is True
    assert buckets.delete_all_project_buckets_calls == [project_id]
    assert storage.delete_bucket_calls == [project_experiment_bucket_name(project_id, None)]
    assert repo.deleted_all_blobs_for == project_id
    assert repo.deleted_all_snapshots_for == project_id
    assert repo.commit_calls == 1


@pytest.mark.asyncio
async def test_prepare_snapshot_download_includes_missing_manifest_file() -> None:
    project_id = uuid4()
    present_hash = "a" * 64
    missing_hash = "b" * 64
    repo = FakeRepository()
    repo.snapshot_to_return = SimpleNamespace(
        manifest=[
            {"path": "existing.bin", "hash": present_hash},
            {"path": "missing.bin", "hash": missing_hash},
        ]
    )
    storage = FakeStorage()
    bucket_name = project_experiment_bucket_name(project_id, None)
    storage.stat_blob_map[(bucket_name, present_hash)] = True
    storage.stat_blob_map[(bucket_name, missing_hash)] = False
    storage.object_payloads[(bucket_name, present_hash)] = b"existing-content"
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    zip_path, _ = await service.prepare_project_snapshot_download(project_id, uuid4())

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        assert set(zip_file.namelist()) == {
            "existing.bin",
            "__missing_blobs_manifest__.txt",
        }
        assert zip_file.read("existing.bin") == b"existing-content"
        missing_manifest = zip_file.read("__missing_blobs_manifest__.txt").decode("utf-8")
        assert f"missing.bin: {missing_hash}" in missing_manifest


@pytest.mark.asyncio
async def test_prepare_snapshot_download_rejects_invalid_manifest_paths() -> None:
    project_id = uuid4()
    repo = FakeRepository()
    repo.snapshot_to_return = SimpleNamespace(
        manifest=[{"path": "bad:path.txt", "hash": "c" * 64}]
    )
    storage = FakeStorage()
    buckets = FakeBucketsService(storage)
    service = ObjectStorageService(repo, buckets, FakeExperimentArtifactsRepository())

    with pytest.raises(HTTPException, match="Invalid path in snapshot") as exc_info:
        await service.prepare_project_snapshot_download(project_id, uuid4())

    assert exc_info.value.status_code == 400
