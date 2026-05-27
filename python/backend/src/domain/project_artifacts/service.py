"""Project artifacts service: check, upload, download, snapshots, delete."""

from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi_users.models import UserProtocol

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

from .error import ProjectArtifactsNotAccessibleError


class ProjectArtifactsService:
    """Application service for project-scoped content-addressed artifacts.

    This service enforces project artifact permissions and delegates all blob,
    snapshot, and CAS metadata operations to the object-storage satellite. It does
    not write to scalars or backend Postgres directly.
    """

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
        """Check which project artifact hashes are missing.

        Args:
            user: User preparing to upload artifacts.
            project_id: Project CAS namespace to inspect.
            hashes: Content hashes to check.

        Returns:
            CheckProjectArtifactsResponseDTO: Missing hashes that require upload.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot log artifacts in
                the project.
            httpx.HTTPError: Propagated by the object-storage client on upstream
                failures.
        """
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.check_project_artifacts(project_id, hashes)

    async def upload_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str, file: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        """Upload one project artifact blob to object storage.

        Args:
            user: User uploading the artifact.
            project_id: Project CAS namespace.
            artifact_hash: Expected content hash used as the logical key.
            file: Multipart upload stream.

        Returns:
            UploadProjectArtifactResponseDTO: Object-storage upload result.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot log artifacts.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.upload_project_artifact(
            project_id, artifact_hash, file
        )

    async def download_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> bytes:
        """Download one project artifact by hash.

        Args:
            user: User requesting the artifact.
            project_id: Project CAS namespace.
            artifact_hash: Content hash to fetch.

        Returns:
            bytes: Raw artifact content.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot view artifacts.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_view_permission(user, project_id)
        return await self._object_storage.download_project_artifact(
            project_id, artifact_hash
        )

    async def create_project_snapshot(
        self, user: UserProtocol, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a project snapshot referencing CAS artifacts.

        Args:
            user: User creating the snapshot.
            project_id: Project that owns the snapshot.
            payload: Snapshot metadata and artifact references.

        Returns:
            SnapshotCreateResponseDTO: Snapshot creation result.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot log artifacts.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.create_project_snapshot(project_id, payload)

    async def download_project_snapshot(
        self, user: UserProtocol, project_id: UUID, snapshot_id: UUID
    ) -> bytes:
        """Download a project snapshot archive.

        Args:
            user: User requesting the snapshot.
            project_id: Project that owns the snapshot.
            snapshot_id: Snapshot identifier.

        Returns:
            bytes: ZIP archive content returned by object storage.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot view artifacts.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_view_permission(user, project_id)
        response = await self._object_storage.download_project_snapshot(
            project_id, snapshot_id
        )
        return response.content

    async def delete_project_artifact(
        self, user: UserProtocol, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        """Delete one project artifact from CAS storage.

        Args:
            user: User deleting the artifact.
            project_id: Project CAS namespace.
            artifact_hash: Content hash to delete.

        Returns:
            DeleteProjectArtifactResponseDTO: Object-storage deletion result.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot log artifacts.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_log_permission(user, project_id)
        return await self._object_storage.delete_project_artifact(
            project_id, artifact_hash
        )

    async def delete_project(
        self, user: UserProtocol, project_id: UUID
    ) -> DeleteProjectResponseDTO:
        """Delete all project artifact storage for a project.

        Args:
            user: User requesting project artifact cleanup.
            project_id: Project whose artifacts, snapshots, and metadata are removed.

        Returns:
            DeleteProjectResponseDTO: Object-storage project deletion result.

        Raises:
            ProjectArtifactsNotAccessibleError: If the user cannot delete the project.
            httpx.HTTPError: Propagated by the object-storage client.
        """
        await self._ensure_delete_project_permission(user, project_id)
        return await self._object_storage.delete_project(project_id)
