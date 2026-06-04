"""No-op project artifacts service when object storage is disabled."""

from __future__ import annotations

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

from .error import ProjectArtifactsNotAccessibleError


class NoOpProjectArtifactsService:
    """Fallback project-artifacts service used when object storage is disabled.

    Basic CAS check/upload/delete methods return benign DTOs so callers can run
    in reduced local/test environments; snapshot and byte reads raise an
    accessibility error because they require object storage state.
    """

    async def ensure_view_project_artifacts(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
        """Allow metadata-only authorization checks in no-storage environments."""

    async def ensure_log_project_artifacts(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
        """Allow metadata-only authorization checks in no-storage environments."""

    async def check_project_artifacts(
        self, user: UserProtocol, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO:
        """Report every requested hash as missing.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            hashes: Hashes to check.

        Returns:
            CheckProjectArtifactsResponseDTO: All hashes in ``missing``.
        """
        return CheckProjectArtifactsResponseDTO(missing=hashes)

    async def upload_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str, file: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        """Return a successful no-op upload result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            artifact_hash: Ignored artifact hash.
            file: Ignored upload stream.

        Returns:
            UploadProjectArtifactResponseDTO: Benign upload status.
        """
        return UploadProjectArtifactResponseDTO(status="ok")

    async def download_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> bytes:
        """Reject project artifact downloads when storage is disabled.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            artifact_hash: Ignored artifact hash.

        Raises:
            ProjectArtifactsNotAccessibleError: Always raised because bytes are not
                available without object storage.

        Returns:
            Never returns successfully.
        """
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Reject snapshot creation when storage is disabled.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            payload: Ignored snapshot payload.

        Raises:
            ProjectArtifactsNotAccessibleError: Always raised because snapshots
                require object-storage metadata.
        """
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def get_project_snapshot_manifest(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> SnapshotManifestResponseDTO:
        """Reject snapshot manifest reads when storage is disabled."""
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response:
        """Reject snapshot downloads when storage is disabled."""
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def delete_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> DeleteProjectSnapshotResponseDTO:
        """Reject snapshot deletion when storage is disabled."""
        raise ProjectArtifactsNotAccessibleError("Project artifacts unavailable")

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        """Return a successful no-op artifact deletion result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.
            artifact_hash: Ignored artifact hash.

        Returns:
            DeleteProjectArtifactResponseDTO: Benign deletion status.
        """
        return DeleteProjectArtifactResponseDTO(deleted=True)

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO:
        """Return a successful no-op project artifact cleanup result.

        Args:
            user: Ignored user context.
            project_id: Ignored project id.

        Returns:
            DeleteProjectResponseDTO: Benign project deletion status.
        """
        return DeleteProjectResponseDTO(deleted=True)
