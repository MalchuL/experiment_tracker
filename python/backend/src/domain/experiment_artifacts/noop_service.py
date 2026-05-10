"""No-op experiment artifacts service when object storage is disabled."""

from __future__ import annotations

from uuid import UUID

from fastapi import UploadFile
from fastapi_users.models import UserProtocol

from clients.artifacts_info import (
    ArtifactType,
    ArtifactsInfoResultDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
)
from lib.pagination import ListOptions

from .dto import (
    ExperimentArtifactDownloadDTO,
    ExperimentArtifactDTO,
    ExperimentArtifactListResponseDTO,
)
from .error import ExperimentArtifactsNotAccessibleError


class NoOpExperimentArtifactsService:
    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        file_paths: list[str] | None = None,
    ) -> ExperimentArtifactListResponseDTO:
        return ExperimentArtifactListResponseDTO(
            data=[],
            has_next=False,
            size=0,
            total=0,
        )

    async def get_experiments_artifacts_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[ArtifactType] | None = None,
        artifact_names: list[str] | None = None,
        steps: list[int] | None = None,
        list_options: ListOptions = ListOptions(),
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        return ArtifactsInfoResultDTO(data=[], has_next=False, size=0, total=0)

    async def upload_and_log_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: ArtifactType,
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
        artifact_type: ArtifactType | None = None,
    ) -> ExperimentArtifactDownloadDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact_by_hash(
        self, user: UserProtocol, experiment_id: UUID, hash: str
    ) -> DeleteExperimentArtifactResponseDTO:
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_experiment_all_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)

    async def delete_experiment_tracked_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        *,
        filepath: str,
    ) -> DeleteExperimentArtifactResponseDTO:
        return DeleteExperimentArtifactResponseDTO(deleted=True)

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
    ) -> ExperimentArtifactDownloadDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

