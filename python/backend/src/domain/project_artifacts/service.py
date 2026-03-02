"""Project artifacts service: check, upload, download, snapshots, delete."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import UploadFile

from clients.object_storage import (
    CheckProjectArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    ObjectStorageClientProtocol,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadProjectArtifactResponseDTO,
)
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .error import ProjectArtifactsNotAccessibleError


class ProjectArtifactsServiceProtocol(Protocol):
    async def check_project_artifacts(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO: ...

    async def upload_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str, file: UploadFile
    ) -> UploadProjectArtifactResponseDTO: ...

    async def download_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> bytes: ...

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO: ...

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes: ...

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO: ...

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO: ...


class NoOpProjectArtifactsService:
    async def check_project_artifacts(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO:
        return CheckProjectArtifactsResponseDTO(missing=hashes)

    async def upload_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str, file: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        return UploadProjectArtifactResponseDTO(status="ok")

    async def download_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
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

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        return DeleteProjectArtifactResponseDTO(deleted=True)

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO:
        return DeleteProjectResponseDTO(deleted=True)


class ProjectArtifactsService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClientProtocol,
        permission_checker: PermissionChecker,
    ):
        self._object_storage = object_storage_client
        self._permission_checker = permission_checker

    async def _ensure_view_permission(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
        if not await self._permission_checker.can_view_artifact(user.id, project_id):
            raise ProjectArtifactsNotAccessibleError(
                f"You are not allowed to view artifacts in project {project_id}"
            )

    async def _ensure_log_permission(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
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

    async def check_project_artifacts(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.check_project_artifacts(project_id, hashes)

    async def upload_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str, file: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.upload_project_artifact(
            project_id, artifact_hash, file
        )

    async def download_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> bytes:
        await self._ensure_view_permission(user, project_id)
        return await self._object_storage.download_project_artifact(
            project_id, artifact_hash
        )

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.create_project_snapshot(project_id, payload)

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes:
        await self._ensure_view_permission(user, project_id)
        response = await self._object_storage.download_project_snapshot(
            project_id, snapshot_id
        )
        return response.content

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.delete_project_artifact(
            project_id, artifact_hash
        )

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO:
        await self._ensure_delete_project_permission(user, project_id)
        return await self._object_storage.delete_project(project_id)
