"""Project artifacts service protocol."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import httpx
from fastapi import UploadFile
from fastapi_users.models import UserProtocol

from clients.object_storage import (
    CheckProjectArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectSnapshotResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    SnapshotManifestResponseDTO,
    UploadProjectArtifactResponseDTO,
)


class ProjectArtifactsServiceProtocol(Protocol):
    async def ensure_view_project_artifacts(
        self, user: UserProtocol, project_id: UUID
    ) -> None: ...

    async def ensure_log_project_artifacts(
        self, user: UserProtocol, project_id: UUID
    ) -> None: ...

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

    async def get_project_snapshot_manifest(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> SnapshotManifestResponseDTO: ...

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response: ...

    async def delete_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> DeleteProjectSnapshotResponseDTO: ...

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO: ...

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO: ...
