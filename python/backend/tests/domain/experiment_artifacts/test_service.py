from __future__ import annotations

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

from clients.object_storage.protocol import ObjectStorageClientProtocol
from clients.object_storage import UploadExperimentArtifactResponseDTO
from domain.experiment_artifacts.repository import ExperimentArtifactRepository
from domain.experiment_artifacts.error import ExperimentArtifactNotFoundError
from domain.experiment_artifacts.service import ExperimentArtifactsService
from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from models import ExperimentArtifact


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FakeArtifactsInfoClient:
    async def get_artifacts(self, *args, **kwargs):
        return SimpleNamespace(data=[])

    async def log_artifact(self, *args, **kwargs):
        return SimpleNamespace(status="logged")


class FakePermissionChecker:
    async def can_log_artifact(self, *args, **kwargs) -> bool:
        return True

    async def can_view_artifact(self, *args, **kwargs) -> bool:
        return True


class FakeExperimentRepository:
    def __init__(self, project_id: UUID) -> None:
        self._project_id = project_id

    async def get_by_id(self, experiment_id: UUID):
        return SimpleNamespace(id=experiment_id, project_id=self._project_id)


class FakeArtifactRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[UUID, str, str], ExperimentArtifact] = {}
        self._by_id: dict[UUID, tuple[UUID, str, str]] = {}

    async def get_by_identity(self, experiment_id: UUID, name: str, filepath: str):
        return self._items.get((experiment_id, name, filepath))

    async def list_by_name(self, experiment_id: UUID, name: str):
        return [
            item
            for (exp_id, item_name, _), item in self._items.items()
            if exp_id == experiment_id and item_name == name
        ]

    async def update(self, artifact_id: UUID, **kwargs):
        key = self._by_id[artifact_id]
        item = self._items[key]
        for field_name, value in kwargs.items():
            setattr(item, field_name, value)
        item.updated_at = _utc_now()
        return item

    async def create(self, obj: ExperimentArtifact):
        if obj.id is None:
            obj.id = uuid4()
        now = _utc_now()
        obj.created_at = now
        obj.updated_at = now
        key = (obj.experiment_id, obj.name, obj.filepath)
        self._items[key] = obj
        self._by_id[obj.id] = key
        return obj

    async def delete_by_identity(self, experiment_id: UUID, name: str, filepath: str) -> int:
        key = (experiment_id, name, filepath)
        item = self._items.pop(key, None)
        if item is None:
            return 0
        self._by_id.pop(item.id, None)
        return 1

    async def delete_by_name(self, experiment_id: UUID, name: str) -> int:
        keys = [
            key
            for key in self._items
            if key[0] == experiment_id and key[1] == name
        ]
        for key in keys:
            item = self._items.pop(key)
            self._by_id.pop(item.id, None)
        return len(keys)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeObjectStorageClient:
    def __init__(self) -> None:
        self.objects: dict[tuple[UUID, str], bytes] = {}
        self.deleted_paths: list[tuple[UUID, str]] = []

    async def upload_experiment_artifact(
        self, experiment_id: UUID, file: UploadFile, path: str | None = None
    ):
        file.file.seek(0)
        content = file.file.read()
        object_path = path or uuid4().hex
        self.objects[(experiment_id, object_path)] = content
        return UploadExperimentArtifactResponseDTO(path=object_path, size=len(content))

    async def download_experiment_artifact(self, experiment_id: UUID, path: str):
        return SimpleNamespace(content=self.objects[(experiment_id, path)])

    async def delete_experiment_artifact(self, experiment_id: UUID, path: str):
        self.deleted_paths.append((experiment_id, path))
        self.objects.pop((experiment_id, path), None)
        return SimpleNamespace(deleted=True)


@pytest.mark.asyncio
async def test_upsert_artifact_replaces_previous_storage_object() -> None:
    experiment_id = uuid4()
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    repository = FakeArtifactRepository()
    service = ExperimentArtifactsService(
        object_storage_client=cast(ObjectStorageClientProtocol, storage),
        artifacts_info_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(project_id)
        ),
        artifact_repository=cast(ExperimentArtifactRepository, repository),
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

    assert first.storage_path == second.storage_path
    assert second.filename == "config-v2.yaml"
    assert storage.deleted_paths == [(experiment_id, first.storage_path)]


@pytest.mark.asyncio
async def test_download_archive_contains_all_files_for_name(tmp_path: Path) -> None:
    experiment_id = uuid4()
    project_id = uuid4()
    storage = FakeObjectStorageClient()
    repository = FakeArtifactRepository()
    service = ExperimentArtifactsService(
        object_storage_client=cast(ObjectStorageClientProtocol, storage),
        artifacts_info_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(project_id)
        ),
        artifact_repository=cast(ExperimentArtifactRepository, repository),
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
            file=UploadFile(filename=Path(relative_path).name, file=io.BytesIO(content)),
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
        object_storage_client=cast(ObjectStorageClientProtocol, FakeObjectStorageClient()),
        artifacts_info_client=FakeArtifactsInfoClient(),
        permission_checker=cast(PermissionChecker, FakePermissionChecker()),
        experiment_repository=cast(
            ExperimentRepository, FakeExperimentRepository(uuid4())
        ),
        artifact_repository=cast(
            ExperimentArtifactRepository, FakeArtifactRepository()
        ),
    )

    with pytest.raises(ExperimentArtifactNotFoundError):
        await service.get_experiment_artifact(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=uuid4(),
            name="configs",
            filepath="missing.yaml",
        )
