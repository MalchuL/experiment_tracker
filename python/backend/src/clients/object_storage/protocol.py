from __future__ import annotations

from typing import Protocol
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadExperimentArtifactResponseDTO,
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

    async def upload_experiment_artifact(
        self, experiment_id: UUID, file: UploadFile
    ) -> UploadExperimentArtifactResponseDTO:
        """Upload an experiment artifact to the object storage.

        Args:
            experiment_id: The ID of the experiment.
            file: The upload file.
        """

    async def download_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> httpx.Response:
        """Download an experiment artifact from the object storage.

        Args:
            experiment_id: The ID of the experiment.
            path: The path of the experiment artifact.
        """

    async def delete_experiment_artifact(
        self, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        """Delete an experiment artifact from the object storage.

        Args:
            experiment_id: The ID of the experiment.
            path: The path of the experiment artifact.
        """

    async def delete_experiment_artifacts(
        self, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        """Delete all experiment artifacts from the object storage.

        Args:
            experiment_id: The ID of the experiment.
        """
