"""No-op experiment artifacts service when object storage is disabled."""

from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi_users.models import UserProtocol

from clients.artifacts_info import (
    ArtifactsInfoResultDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
)

from .dto import (
    ExperimentArtifactAtStepDownloadDTO,
    ExperimentArtifactDTO,
)
from .error import ExperimentArtifactsNotAccessibleError


class NoOpExperimentArtifactsService:
    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        file_paths: list[str] | None = None,
    ) -> list[ExperimentArtifactDTO]:
        return []

    async def get_experiments_artifacts_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        steps: list[int] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        return ArtifactsInfoResultDTO(data=[])

    async def upload_and_log_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> ArtifactsInfoLogArtifactResponseDTO:
        return ArtifactsInfoLogArtifactResponseDTO(status="logged")

    async def download_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> ExperimentArtifactAtStepDownloadDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact_by_hash(
        self, user: UserProtocol, experiment_id: UUID, hash: str
    ) -> DeleteExperimentArtifactResponseDTO:
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_experiment_all_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str | None,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> tuple[bytes, str, str]:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

