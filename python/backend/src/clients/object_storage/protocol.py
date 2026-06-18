from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

import httpx
from fastapi import UploadFile

from .dto import (
    StorageBucketListResponseDTO,
    StorageBucketClearResponseDTO,
    StorageBucketDeleteResponseDTO,
    StorageBucketReconcileResponseDTO,
    CheckProjectArtifactsResponseDTO,
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    DeleteProjectArtifactResponseDTO,
    DeleteProjectSnapshotResponseDTO,
    DeleteProjectResponseDTO,
    EnsureExperimentBucketResponseDTO,
    EnsureProjectBucketResponseDTO,
    ExperimentArtifactsUsageResponseDTO,
    ExperimentTrackedArtifactListDTO,
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedUploadResponseDTO,
    ExperimentUntrackedUploadResponseDTO,
    ProjectUsageResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    SnapshotManifestResponseDTO,
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

    async def ensure_project_bucket(
        self, project_id: UUID
    ) -> EnsureProjectBucketResponseDTO:
        """Ensure the project-scoped CAS bucket exists in object storage."""

    async def ensure_experiment_bucket(
        self, project_id: UUID, experiment_id: UUID
    ) -> EnsureExperimentBucketResponseDTO:
        """Ensure the experiment-scoped bucket exists in object storage."""

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

    async def get_project_snapshot_manifest(
        self, project_id: UUID, snapshot_id: UUID
    ) -> SnapshotManifestResponseDTO:
        """Return snapshot manifest metadata without downloading the ZIP archive."""

    async def download_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> httpx.Response:
        """Download a project snapshot ZIP archive."""

    async def delete_project_snapshot(
        self, project_id: UUID, snapshot_id: UUID
    ) -> DeleteProjectSnapshotResponseDTO: ...

    async def get_project_usage(self, project_id: UUID) -> ProjectUsageResponseDTO:
        """GET aggregated byte/count stats for project-scoped buckets and CAS artifacts."""

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

    async def cleanup_project_cas_only(self, project_id: UUID) -> DeleteProjectResponseDTO: ...

    async def cleanup_project_snapshots_only(
        self, project_id: UUID
    ) -> DeleteProjectResponseDTO: ...

    async def cleanup_project_experiment_buckets_only(
        self, project_id: UUID
    ) -> DeleteProjectResponseDTO: ...

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

    async def delete_tracked_experiment_artifacts(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...

    async def delete_untracked_experiment_blobs(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ExperimentArtifactsUsageResponseDTO:
        """GET counts/bytes for experiment artifacts (named + at-step) in object storage."""

    async def list_buckets(
        self,
        project_id: UUID | None = None,
        experiment_id: UUID | None = None,
        reconcile: bool = False,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> StorageBucketListResponseDTO: ...

    async def delete_bucket(self, bucket_id: UUID) -> StorageBucketDeleteResponseDTO: ...

    async def delete_storage_only_bucket(
        self, name: str
    ) -> StorageBucketDeleteResponseDTO: ...

    async def clear_storage_only_bucket(
        self, name: str
    ) -> StorageBucketClearResponseDTO: ...

    async def clear_bucket(self, bucket_id: UUID) -> StorageBucketClearResponseDTO: ...

    async def reconcile_bucket(
        self, bucket_id: UUID
    ) -> StorageBucketReconcileResponseDTO: ...
