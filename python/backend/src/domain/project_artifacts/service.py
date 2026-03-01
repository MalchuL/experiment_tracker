"""Project artifacts service: get metadata, blobs, snapshots, delete."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Sequence
from uuid import UUID

from fastapi import UploadFile

from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from clients.artifacts_info_client import ArtifactsInfoClientProtocol
from clients.object_storage_client import ObjectStorageClient
from .dto import (
    LogArtifactRequestDTO,
    LogArtifactResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
)
from .error import ProjectArtifactsNotAccessibleError


class ProjectArtifactsServiceProtocol(Protocol):
    async def upload_and_log_artifact(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: str,
        step: int,
        blob_hash: str,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> LogArtifactResponseDTO: ...

    async def get_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        artifact_types: Sequence[str] | None = None,
        artifact_names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]: ...

    async def check_project_blobs(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> dict[str, Any]: ...

    async def upload_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str, file: UploadFile
    ) -> dict[str, Any]: ...

    async def download_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> bytes: ...

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO: ...

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes: ...

    async def delete_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> dict[str, Any]: ...

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> dict[str, Any]: ...


class NoOpProjectArtifactsService:
    async def upload_and_log_artifact(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: str,
        step: int,
        blob_hash: str,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> LogArtifactResponseDTO:
        return LogArtifactResponseDTO(status="logged")

    async def get_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        artifact_types: Sequence[str] | None = None,
        artifact_names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        return {"data": []}

    async def check_project_blobs(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> dict[str, Any]:
        return {"missing": hashes}

    async def upload_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str, file: UploadFile
    ) -> dict[str, Any]:
        return {"status": "ok"}

    async def download_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> bytes:
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        return SnapshotCreateResponseDTO(snapshot_id="")

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes:
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def delete_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> dict[str, Any]:
        return {"deleted": True}

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> dict[str, Any]:
        return {"deleted": True}


class ProjectArtifactsService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClient,
        artifacts_info_client: ArtifactsInfoClientProtocol,
        permission_checker: PermissionChecker,
    ):
        self._object_storage = object_storage_client
        self._artifacts_info = artifacts_info_client
        self._permission_checker = permission_checker

    async def _ensure_view_permission(self, user: UserProtocol, project_id: UUID) -> None:
        if not await self._permission_checker.can_view_artifact(user.id, project_id):
            raise ProjectArtifactsNotAccessibleError(
                f"You are not allowed to view artifacts in project {project_id}"
            )

    async def _ensure_log_permission(self, user: UserProtocol, project_id: UUID) -> None:
        if not await self._permission_checker.can_log_artifact(user.id, project_id):
            raise ProjectArtifactsNotAccessibleError(
                f"You are not allowed to log artifacts in project {project_id}"
            )

    async def _ensure_delete_project_permission(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
        if not await self._permission_checker.can_delete_project(user.id, project_id):
            raise ProjectArtifactsNotAccessibleError(
                f"You are not allowed to delete project {project_id}"
            )

    async def upload_and_log_artifact(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: str,
        step: int,
        blob_hash: str,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> LogArtifactResponseDTO:
        await self._ensure_log_permission(user, project_id)
        content = await file.read()

        file.file.seek(0)
        await self._object_storage.upload_project_blob(
            project_id, blob_hash, file
        )

        payload_metadata: dict[str, str] = {
            "filename": file.filename or f"{name}_{step}",
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": str(len(content)),
        }
        if metadata:
            payload_metadata.update(metadata)

        payload = LogArtifactRequestDTO(
            name=name,
            artifact_type=artifact_type,
            path=blob_hash,
            step=step,
            metadata=payload_metadata,
            tags=tags or [],
        )
        result = await self._artifacts_info.log_artifact(
            project_id, experiment_id, payload.model_dump()
        )
        return LogArtifactResponseDTO.model_validate(result)

    async def get_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: Sequence[UUID] | None = None,
        artifact_types: Sequence[str] | None = None,
        artifact_names: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        await self._ensure_view_permission(user, project_id)
        return await self._artifacts_info.get_artifacts(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
        )

    async def check_project_blobs(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> dict[str, Any]:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.check_project_blobs(project_id, hashes)

    async def upload_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str, file: UploadFile
    ) -> dict[str, Any]:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.upload_project_blob(
            project_id, blob_hash, file
        )

    async def download_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> bytes:
        await self._ensure_view_permission(user, project_id)
        return await self._object_storage.download_project_blob(
            project_id, blob_hash
        )

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        await self._ensure_log_permission(user, project_id)
        result = await self._object_storage.create_project_snapshot(
            payload.model_dump(mode="json")
        )
        return SnapshotCreateResponseDTO.model_validate(result)

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes:
        await self._ensure_view_permission(user, project_id)
        response = await self._object_storage.download_project_snapshot(
            project_id, snapshot_id
        )
        return response.content

    async def delete_project_blob(
        self, user: UserProtocol, project_id: UUID, blob_hash: str
    ) -> dict[str, Any]:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.delete_project_blob(
            project_id, blob_hash
        )

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> dict[str, Any]:
        await self._ensure_delete_project_permission(user, project_id)
        await self._object_storage.delete_project(project_id)
        return {"deleted": True}
