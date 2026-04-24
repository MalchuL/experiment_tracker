from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from clients.artifacts_info import (
    ArtifactInfoEntryDTO,
    ArtifactsInfoResultDTO,
    ExperimentArtifactsInfoDTO,
    LogArtifactRequestDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ExperimentTrackedArtifactListDTO,
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedArtifactItemDTO,
    ExperimentTrackedUploadResponseDTO,
    ExperimentUntrackedUploadResponseDTO,
)
from clients.object_storage.protocol import ObjectStorageClientProtocol
from domain.experiment_artifacts.error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactAmbiguousError,
    ExperimentArtifactNotFoundError,
)
from domain.experiment_artifacts.service import ExperimentArtifactsService
from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker


class FakeArtifactsInfoClient:
    async def get_artifacts(self, *args, **kwargs):
        return SimpleNamespace(data=[])

    async def log_artifact_at_step(self, *args, **kwargs):
        return SimpleNamespace(status="logged")


class RecordingArtifactsInfoClient(FakeArtifactsInfoClient):
    def __init__(self) -> None:
        self.get_artifacts_calls: list[dict] = []
        self.log_calls: list[tuple[UUID, UUID, LogArtifactRequestDTO]] = []

    async def get_artifacts(self, **kwargs):
        self.get_artifacts_calls.append(kwargs)
        return ArtifactsInfoResultDTO(data=[], total=0)

    async def log_artifact_at_step(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ):
        self.log_calls.append((project_id, experiment_id, payload))
        return SimpleNamespace(status="logged")


class MirroringArtifactsInfoClient(FakeArtifactsInfoClient):
    """Keeps logged rows in memory and applies the same filters as scalars for get_artifacts."""

    def __init__(self) -> None:
        self._rows: list[tuple[UUID, UUID, LogArtifactRequestDTO]] = []

    async def log_artifact_at_step(
        self, project_id: UUID, experiment_id: UUID, payload: LogArtifactRequestDTO
    ):
        self._rows.append((project_id, experiment_id, payload))
        return SimpleNamespace(status="logged")

    async def get_artifacts(self, **kwargs):
        project_id = kwargs["project_id"]
        experiment_ids = list(kwargs.get("experiment_ids") or [])
        artifact_names = list(kwargs.get("artifact_names") or [])
        artifact_types = list(kwargs.get("artifact_types") or [])
        steps = list(kwargs.get("steps") or [])

        by_exp: dict[UUID, list[ArtifactInfoEntryDTO]] = {}
        for pid, eid, p in self._rows:
            if pid != project_id:
                continue
            if experiment_ids and eid not in experiment_ids:
                continue
            if artifact_names and p.name not in artifact_names:
                continue
            if steps and p.step not in steps:
                continue
            if artifact_types and p.artifact_type not in artifact_types:
                continue
            entry = ArtifactInfoEntryDTO(
                timestamp=datetime.now(timezone.utc),
                step=p.step,
                name=p.name,
                artifact_type=p.artifact_type,
                path=p.path,
                metadata=p.metadata or {},
                tags=p.tags or [],
            )
            by_exp.setdefault(eid, []).append(entry)

        grouped_items = [
            ExperimentArtifactsInfoDTO(experiment_id=eid, artifacts_info=items)
            for eid, items in by_exp.items()
        ]
        limit = kwargs.get("limit")
        offset = kwargs.get("offset") or 0
        total = len(grouped_items)
        if limit is None:
            return ArtifactsInfoResultDTO(
                data=grouped_items,
                has_next=False,
                size=len(grouped_items),
                total=total,
            )
        page = grouped_items[offset : offset + int(limit)]
        return ArtifactsInfoResultDTO(
            data=page,
            has_next=offset + len(page) < total,
            size=len(page),
            total=total,
        )


class FakePermissionChecker:
    async def can_log_artifact(self, *args, **kwargs) -> bool:
        return True

    async def can_view_artifact(self, *args, **kwargs) -> bool:
        return True


class DenyViewPermissionChecker:
    async def can_log_artifact(self, *args, **kwargs) -> bool:
        return True

    async def can_view_artifact(self, *args, **kwargs) -> bool:
        return False


class DenyLogPermissionChecker:
    async def can_log_artifact(self, *args, **kwargs) -> bool:
        return False

    async def can_view_artifact(self, *args, **kwargs) -> bool:
        return True


class FakeExperimentRepository:
    def __init__(self, project_id: UUID) -> None:
        self._project_id = project_id

    async def get_by_id(self, experiment_id: UUID):
        return SimpleNamespace(id=experiment_id, project_id=self._project_id)


class TrackedRow:
    __slots__ = ("id", "hash", "file_path", "mime_type", "size", "metadata")

    def __init__(
        self,
        row_id: UUID,
        hash: str,
        file_path: str,
        mime_type: str,
        size: int,
        metadata: dict | None = None,
    ) -> None:
        self.id = row_id
        self.hash = hash
        self.file_path = file_path
        self.mime_type = mime_type
        self.size = size
        self.metadata = metadata or {}


class FakeObjectStorageClient:
    def __init__(self) -> None:
        self.blobs: dict[tuple[UUID, UUID, str], bytes] = {}
        self.tracked: dict[tuple[UUID, UUID], list[TrackedRow]] = {}
        self.deleted_hashes: list[tuple[UUID, UUID, str]] = []

    async def upload_experiment_untracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
    ):
        await file.seek(0)
        content = await file.read()
        await file.seek(0)
        h = artifact_hash or uuid4().hex
        self.blobs[(project_id, experiment_id, h)] = content
        return ExperimentUntrackedUploadResponseDTO(hash=h, size=len(content))

    async def upload_experiment_tracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
        file_path: str | None = None,
        content_type: str | None = None,
        metadata: dict | None = None,
    ):
        await file.seek(0)
        content = await file.read()
        await file.seek(0)
        h = artifact_hash or hashlib.sha256(content).hexdigest()
        file_path = file_path or (file.filename or "file")
        key = (project_id, experiment_id)
        rows = self.tracked.setdefault(key, [])
        kept: list[TrackedRow] = []
        for r in rows:
            if r.file_path == file_path:
                self.blobs.pop((project_id, experiment_id, r.hash), None)
                self.deleted_hashes.append((project_id, experiment_id, r.hash))
            else:
                kept.append(r)
        self.blobs[(project_id, experiment_id, h)] = content
        meta = dict(metadata or {})
        row = TrackedRow(
            uuid4(),
            h,
            file_path,
            content_type or file.content_type or "application/octet-stream",
            len(content),
            metadata=meta,
        )
        kept.append(row)
        self.tracked[key] = kept
        return ExperimentTrackedUploadResponseDTO(
            id=row.id,
            hash=row.hash,
            file_path=row.file_path,
            mime_type=row.mime_type,
            size=row.size,
            metadata=row.metadata,
        )

    async def list_experiment_tracked_artifacts(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        file_paths: list[str] | None = None,
    ):
        rows = self.tracked.get((project_id, experiment_id), [])
        if file_paths:
            rows = [row for row in rows if row.file_path in set(file_paths)]
        chunk = rows[offset : offset + limit]
        data = [
            ExperimentTrackedArtifactItemDTO(
                id=r.id,
                hash=r.hash,
                file_path=r.file_path,
                mime_type=r.mime_type,
                size=r.size,
                metadata=r.metadata,
            )
            for r in chunk
        ]
        return ExperimentTrackedArtifactListDTO(
            data=data,
            has_next=offset + len(data) < len(rows),
            size=len(data),
            total=len(rows),
        )

    async def get_experiment_tracked_artifact_info(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        file_path: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ):
        rows = self.tracked.get((project_id, experiment_id), [])
        for r in rows:
            if file_path is not None and r.file_path == file_path:
                now = datetime.now(timezone.utc)
                return ExperimentTrackedArtifactInfoDTO(
                    id=r.id,
                    hash=r.hash,
                    file_path=r.file_path,
                    mime_type=r.mime_type,
                    size=r.size,
                    metadata=r.metadata,
                    created_at=now,
                    updated_at=now,
                )
            if artifact_hash is not None and r.hash == artifact_hash:
                now = datetime.now(timezone.utc)
                return ExperimentTrackedArtifactInfoDTO(
                    id=r.id,
                    hash=r.hash,
                    file_path=r.file_path,
                    mime_type=r.mime_type,
                    size=r.size,
                    metadata=r.metadata,
                    created_at=now,
                    updated_at=now,
                )
            if blob_id is not None and r.id == blob_id:
                now = datetime.now(timezone.utc)
                return ExperimentTrackedArtifactInfoDTO(
                    id=r.id,
                    hash=r.hash,
                    file_path=r.file_path,
                    mime_type=r.mime_type,
                    size=r.size,
                    metadata=r.metadata,
                    created_at=now,
                    updated_at=now,
                )
        return None

    async def download_experiment_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        *,
        tracked: bool = False,
    ):
        content = self.blobs[(project_id, experiment_id, artifact_hash)]
        return SimpleNamespace(content=content)

    async def delete_experiment_artifact(
        self, project_id: UUID, experiment_id: UUID, artifact_hash: str
    ):
        self.deleted_hashes.append((project_id, experiment_id, artifact_hash))
        self.blobs.pop((project_id, experiment_id, artifact_hash), None)
        key = (project_id, experiment_id)
        if key in self.tracked:
            self.tracked[key] = [
                r for r in self.tracked[key] if r.hash != artifact_hash
            ]
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_all_experiment_artifacts(
        self, project_id: UUID, experiment_id: UUID
    ):
        key = (project_id, experiment_id)
        for r in self.tracked.get(key, []):
            self.blobs.pop((project_id, experiment_id, r.hash), None)
        self.tracked.pop(key, None)
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)


@pytest.mark.asyncio
async def test_upsert_artifact_replaces_previous_storage_object() -> None:
    experiment_id = uuid4()
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    service = ExperimentArtifactsService(
        object_storage_client=cast(ObjectStorageClientProtocol, storage),
        artifacts_info_at_step_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(project_id)
        ),
    )

    file_v1 = UploadFile(
        filename="config-v1.yaml",
        file=io.BytesIO(b"v1"),
        headers=Headers({"content-type": "text/yaml"}),
    )
    file_v2 = UploadFile(
        filename="config-v2.yaml",
        file=io.BytesIO(b"v2"),
        headers=Headers({"content-type": "text/yaml"}),
    )
    user = SimpleNamespace(id=uuid4())

    first = await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="configs",
        filepath="train/config.yaml",
        file=file_v1,
    )
    second = await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="configs",
        filepath="train/config.yaml",
        file=file_v2,
    )

    assert first.storage_path != second.storage_path
    assert (project_id, experiment_id, first.storage_path) in storage.deleted_hashes
    assert second.filename == "config-v2.yaml"


@pytest.mark.asyncio
async def test_upsert_replaces_visual_name_for_same_filepath() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    user = SimpleNamespace(id=uuid4())

    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="first-name",
        filepath="train/config.yaml",
        file=UploadFile(filename="config-v1.yaml", file=io.BytesIO(b"v1")),
    )
    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="second-name",
        filepath="train/config.yaml",
        file=UploadFile(filename="config-v2.yaml", file=io.BytesIO(b"v2")),
    )

    dto = await service.get_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        filepath="train/config.yaml",
    )
    assert dto.name == "second-name"
    assert dto.filepath == "train/config.yaml"


@pytest.mark.asyncio
async def test_download_archive_contains_all_files_for_name(tmp_path: Path) -> None:
    experiment_id = uuid4()
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    service = ExperimentArtifactsService(
        object_storage_client=cast(ObjectStorageClientProtocol, storage),
        artifacts_info_at_step_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(project_id)
        ),
    )
    user = SimpleNamespace(id=uuid4())

    for relative_path, content in [
        ("epoch-1.pt", b"1"),
        ("nested/epoch-2.pt", b"2"),
    ]:
        await service.upsert_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name="checkpoints",
            filepath=relative_path,
            file=UploadFile(
                filename=Path(relative_path).name, file=io.BytesIO(content)
            ),
        )

    archive_path, filename = await service.download_experiment_artifacts_archive(
        user=user, experiment_id=experiment_id, name="checkpoints"
    )
    assert filename == "checkpoints.zip"
    with zipfile.ZipFile(archive_path, "r") as zf:
        assert sorted(zf.namelist()) == ["epoch-1.pt", "nested/epoch-2.pt"]
        assert zf.read("epoch-1.pt") == b"1"
        assert zf.read("nested/epoch-2.pt") == b"2"


@pytest.mark.asyncio
async def test_get_artifact_raises_not_found() -> None:
    service = ExperimentArtifactsService(
        object_storage_client=cast(
            ObjectStorageClientProtocol, FakeObjectStorageClient()
        ),
        artifacts_info_at_step_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(uuid4())
        ),
    )

    with pytest.raises(ExperimentArtifactNotFoundError):
        await service.get_experiment_artifact(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
            filepath="missing.yaml",
        )


def _make_service(
    storage: FakeObjectStorageClient,
    *,
    info: (
        FakeArtifactsInfoClient
        | RecordingArtifactsInfoClient
        | MirroringArtifactsInfoClient
        | None
    ) = None,
    permission: (
        FakePermissionChecker
        | DenyViewPermissionChecker
        | DenyLogPermissionChecker
        | None
    ) = None,
    project_id: UUID | None = None,
) -> tuple[ExperimentArtifactsService, UUID]:
    pid = project_id or uuid4()
    perm = permission or FakePermissionChecker()
    svc = ExperimentArtifactsService(
        object_storage_client=cast(ObjectStorageClientProtocol, storage),
        artifacts_info_at_step_client=info or FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, perm),
        experiment_repository=cast(ExperimentRepository, FakeExperimentRepository(pid)),
    )
    return svc, pid


@pytest.mark.asyncio
async def test_list_experiment_artifacts_returns_tracked_dtos() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _pid = _make_service(storage)

    await service.upsert_experiment_artifact(
        user=SimpleNamespace(id=uuid4()),
        experiment_id=experiment_id,
        name="weights",
        filepath="a.pt",
        file=UploadFile(filename="a.pt", file=io.BytesIO(b"z")),
    )

    rows = await service.list_experiment_artifacts(
        user=SimpleNamespace(id=uuid4()),
        experiment_id=experiment_id,
    )
    assert rows.size == 1
    assert rows.has_next is False
    assert rows.data[0].filepath == "a.pt"
    assert rows.data[0].metadata.get("name") == "weights"


@pytest.mark.asyncio
async def test_list_experiment_artifacts_filters_by_file_paths() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _pid = _make_service(storage)
    user = SimpleNamespace(id=uuid4())

    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="a",
        filepath="one.bin",
        file=UploadFile(filename="one.bin", file=io.BytesIO(b"1")),
    )
    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="a",
        filepath="two.bin",
        file=UploadFile(filename="two.bin", file=io.BytesIO(b"2")),
    )

    filtered = await service.list_experiment_artifacts(
        user=user,
        experiment_id=experiment_id,
        file_paths=["two.bin"],
    )
    assert filtered.size == 1
    assert filtered.data[0].filepath == "two.bin"


@pytest.mark.asyncio
async def test_list_experiment_artifacts_loads_multiple_pages_from_storage() -> None:
    """``_list_tracked_all`` paginates with limit 100."""

    experiment_id = uuid4()
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    key = (project_id, experiment_id)
    rows: list[TrackedRow] = []
    for i in range(101):
        h = f"{i:064x}"
        fp = f"ns/f{i}.txt"
        rows.append(
            TrackedRow(
                uuid4(),
                h,
                fp,
                "text/plain",
                1,
                metadata={"name": "x"},
            )
        )
        storage.blobs[(project_id, experiment_id, h)] = b"x"
    storage.tracked[key] = rows

    service, _ = _make_service(storage, project_id=project_id)
    out = await service.list_experiment_artifacts(
        user=SimpleNamespace(id=uuid4()),
        experiment_id=experiment_id,
    )
    assert out.size == 100
    assert out.has_next is True


@pytest.mark.asyncio
async def test_get_experiments_artifacts_at_step_forwards_filters() -> None:
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    info = RecordingArtifactsInfoClient()
    service, _ = _make_service(storage, info=info)

    exp_a = uuid4()
    await service.get_experiments_artifacts_at_step(
        user=SimpleNamespace(id=uuid4()),
        project_id=project_id,
        experiment_ids=[exp_a],
        artifact_types=["image"],
        artifact_names=["loss_curve"],
        steps=[10, 20],
        start_time="2020-01-01T00:00:00",
        end_time="2020-02-01T00:00:00",
    )

    assert len(info.get_artifacts_calls) == 1
    call = info.get_artifacts_calls[0]
    assert call["project_id"] == project_id
    assert list(call["experiment_ids"]) == [exp_a]
    assert list(call["artifact_types"]) == ["image"]
    assert list(call["artifact_names"]) == ["loss_curve"]
    assert list(call["steps"]) == [10, 20]
    assert call["start_time"] == "2020-01-01T00:00:00"
    assert call["end_time"] == "2020-02-01T00:00:00"


@pytest.mark.asyncio
async def test_upload_and_log_experiment_artifact_at_step_untracked_plus_log() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    info = RecordingArtifactsInfoClient()
    service, project_id = _make_service(storage, info=info)
    user = SimpleNamespace(id=uuid4())

    body = io.BytesIO(b"png-bytes")
    file = UploadFile(
        filename="shot.png",
        file=body,
        headers=Headers({"content-type": "image/png"}),
    )
    await service.upload_and_log_experiment_artifact_at_step(
        user=user,
        experiment_id=experiment_id,
        file=file,
        name="val_image",
        artifact_type="image",
        step=10,
        metadata={"note": "best"},
        tags=["a", "b"],
    )

    assert len(info.log_calls) == 1
    logged_pid, logged_eid, payload = info.log_calls[0]
    assert logged_pid == project_id
    assert logged_eid == experiment_id
    assert payload.name == "val_image"
    assert payload.artifact_type == "image"
    assert payload.step == 10
    assert payload.tags == ["a", "b"]
    assert payload.metadata is not None
    assert payload.metadata["note"] == "best"
    assert payload.path  # content hash from untracked upload
    assert (project_id, experiment_id, payload.path) in storage.blobs


@pytest.mark.asyncio
async def test_download_experiment_artifact_at_step_reads_untracked_blob() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, project_id = _make_service(storage, info=MirroringArtifactsInfoClient())
    user = SimpleNamespace(id=uuid4())

    uf = UploadFile(filename="x.bin", file=io.BytesIO(b"abc"))
    await service.upload_and_log_experiment_artifact_at_step(
        user=user,
        experiment_id=experiment_id,
        file=uf,
        name="n",
        artifact_type="text",
        step=0,
    )

    out = await service.download_experiment_artifact_at_step(
        user=user,
        experiment_id=experiment_id,
        step=0,
        name="n",
        artifact_type="text",
    )
    assert out.content == b"abc"
    assert out.filename == "x.bin"
    assert out.content_type == "application/octet-stream"


@pytest.mark.asyncio
async def test_download_experiment_artifact_at_step_ambiguous_without_type() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    info = MirroringArtifactsInfoClient()
    service, _ = _make_service(storage, info=info)
    user = SimpleNamespace(id=uuid4())

    for atype in ("image", "text"):
        uf = UploadFile(filename="x.bin", file=io.BytesIO(b"x"))
        await service.upload_and_log_experiment_artifact_at_step(
            user=user,
            experiment_id=experiment_id,
            file=uf,
            name="same",
            artifact_type=atype,
            step=1,
        )

    with pytest.raises(ExperimentArtifactAmbiguousError):
        await service.download_experiment_artifact_at_step(
            user=user,
            experiment_id=experiment_id,
            step=1,
            name="same",
            artifact_type=None,
        )


@pytest.mark.asyncio
async def test_download_named_tracked_returns_bytes_and_filename() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    user = SimpleNamespace(id=uuid4())

    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="m",
        filepath="f.txt",
        file=UploadFile(
            filename="f.txt",
            file=io.BytesIO(b"hello"),
            headers=Headers({"content-type": "text/plain"}),
        ),
    )
    payload = await service.download_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        filepath="f.txt",
    )
    assert payload.content == b"hello"
    assert payload.content_type == "text/plain"
    assert payload.filename == "f.txt"


@pytest.mark.asyncio
async def test_delete_experiment_artifact_by_hash_delegates_to_storage() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    user = SimpleNamespace(id=uuid4())
    uf = UploadFile(filename="x.bin", file=io.BytesIO(b"x"))
    await service.upload_and_log_experiment_artifact_at_step(
        user=user,
        experiment_id=experiment_id,
        file=uf,
        name="n",
        artifact_type="text",
        step=1,
    )
    h = next(iter(storage.blobs.keys()))[2]
    res = await service.delete_experiment_artifact_by_hash(
        user=user, experiment_id=experiment_id, hash=h
    )
    assert res.deleted is True


@pytest.mark.asyncio
async def test_delete_experiment_all_artifacts_delegates() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    user = SimpleNamespace(id=uuid4())
    res = await service.delete_experiment_all_artifacts(
        user=user, experiment_id=experiment_id
    )
    assert res.deleted_count == 0


@pytest.mark.asyncio
async def test_delete_experiment_artifact_by_hash_deletes_matching_row() -> None:
    experiment_id = uuid4()
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    user = SimpleNamespace(id=uuid4())
    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="g",
        filepath="a.pt",
        file=UploadFile(filename="a.pt", file=io.BytesIO(b"1")),
    )
    await service.upsert_experiment_artifact(
        user=user,
        experiment_id=experiment_id,
        name="g",
        filepath="b.pt",
        file=UploadFile(filename="b.pt", file=io.BytesIO(b"2")),
    )
    listed = await service.list_experiment_artifacts(user=user, experiment_id=experiment_id)
    target_hash = listed.data[0].storage_path
    res = await service.delete_experiment_artifact_by_hash(
        user=user,
        experiment_id=experiment_id,
        hash=target_hash,
    )
    assert res.deleted is True
    remaining = await service.list_experiment_artifacts(
        user=user, experiment_id=experiment_id
    )
    assert remaining.size == 1


@pytest.mark.asyncio
async def test_view_permission_denied_on_list() -> None:
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage, permission=DenyViewPermissionChecker())
    with pytest.raises(ExperimentArtifactsNotAccessibleError):
        await service.list_experiment_artifacts(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_log_permission_denied_on_upsert() -> None:
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage, permission=DenyLogPermissionChecker())
    with pytest.raises(ExperimentArtifactsNotAccessibleError):
        await service.upsert_experiment_artifact(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
            name="a",
            filepath="b.txt",
            file=UploadFile(filename="b.txt", file=io.BytesIO(b"x")),
        )


@pytest.mark.asyncio
async def test_download_archive_raises_when_name_has_no_tracked_objects() -> None:
    storage = FakeObjectStorageClient()
    service, _ = _make_service(storage)
    with pytest.raises(ExperimentArtifactNotFoundError):
        await service.download_experiment_artifacts_archive(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
            name="missing",
        )
