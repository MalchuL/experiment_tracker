"""Experiment artifacts service protocol."""

from __future__ import annotations

from typing import Protocol
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


class ExperimentArtifactsServiceProtocol(Protocol):
    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        file_paths: list[str] | None = None,
    ) -> ExperimentArtifactListResponseDTO: ...

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
    ) -> ArtifactsInfoResultDTO: ...

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
    ) -> ArtifactsInfoLogArtifactResponseDTO: ...

    async def download_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        step: int,
        name: str,
        artifact_type: ArtifactType | None = None,
    ) -> ExperimentArtifactDownloadDTO: ...

    async def delete_experiment_artifact_by_hash(
        self, user: UserProtocol, experiment_id: UUID, hash: str
    ) -> DeleteExperimentArtifactResponseDTO: ...

    async def delete_experiment_all_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str | None,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO: ...

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDTO: ...

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDownloadDTO: ...

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]: ...

