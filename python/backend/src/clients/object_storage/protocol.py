from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    ExperimentTrackedArtifactListDTO,
    ExperimentTrackedArtifactItemDTO,
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedUploadResponseDTO,
    ExperimentUntrackedUploadResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadProjectArtifactResponseDTO,
)


class ObjectStorageClientProtocol(Protocol):
    async def check_project_artifacts(
        self, project_id: UUID, hashes: list[str]
    ) -> CheckProjectArtifactsResponseDTO:
        """Check if the project artifacts exist in the object storage.

        Args:
            project_id: The ID of the project.
            hashes: The hashes of the project artifacts.

        Returns:
            The response from the object storage.
        """

    async def upload_project_artifact(
        self, project_id: UUID, artifact_hash: str, upload: UploadFile
    ) -> UploadProjectArtifactResponseDTO:
        """Upload a project artifact to the object storage.

        Args:
            project_id: The ID of the project.
            artifact_hash: The hash of the project artifact.
            upload: The upload file.
        """

    async def download_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> bytes:
        """Download a project artifact from the object storage.

        Args:
            project_id: The ID of the project.
            artifact_hash: The hash of the project artifact.

        Returns:
            The response from the object storage.
        """

    async def create_project_snapshot(
        self, project_id: UUID, payload: SnapshotCreateRequestDTO
    ) -> SnapshotCreateResponseDTO:
        """Create a project snapshot in the object storage.

        Args:
            project_id: The ID of the project.
            payload: The payload to create the project snapshot.

        Returns:
            The response from the object storage.
        """

    async def download_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response:
        """Download a project snapshot from the object storage.

        Args:
            project_id: The ID of the project.
            snapshot_id: The ID of the project snapshot.

        Returns:
            The response from the object storage.
        """

    async def delete_project_artifact(
        self, project_id: UUID, artifact_hash: str
    ) -> DeleteProjectArtifactResponseDTO:
        """Delete a project artifact from the object storage.

        Args:
            project_id: The ID of the project.
            artifact_hash: The hash of the project artifact.

        Returns:
            The response from the object storage.
        """

    async def delete_project(self, project_id: UUID) -> DeleteProjectResponseDTO:
        """Delete a project from the object storage.

        Args:
            project_id: The ID of the project.

        Returns:
            The response from the object storage.
        """

    async def upload_experiment_untracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
    ) -> ExperimentUntrackedUploadResponseDTO: ...

    async def upload_experiment_tracked(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file: UploadFile,
        artifact_hash: str | None = None,
        file_path: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentTrackedUploadResponseDTO: ...

    async def list_experiment_tracked_artifacts(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        file_paths: list[str] | None = None,
    ) -> ExperimentTrackedArtifactListDTO: ...

    async def get_experiment_tracked_artifact_info(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        file_path: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentTrackedArtifactInfoDTO: ...

    async def download_experiment_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        *,
        tracked: bool = False,
    ) -> httpx.Response: ...

    async def delete_experiment_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
    ) -> DeleteExperimentArtifactResponseDTO: ...

    async def delete_all_experiment_artifacts(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...
