"""No-op project artifacts service when object storage is disabled."""

from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi_users.models import UserProtocol

from clients.object_storage import (
    CheckProjectArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadProjectArtifactResponseDTO,
)

from .error import ProjectArtifactsNotAccessibleError


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
