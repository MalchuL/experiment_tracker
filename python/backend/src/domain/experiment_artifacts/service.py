"""Experiment artifacts service: upload, log, download, delete."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import UploadFile

from clients.artifacts_info import (
    ArtifactsInfoClientProtocol,
    ArtifactsInfoResultDTO,
    LogArtifactRequestDTO as ArtifactsInfoLogArtifactRequestDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ObjectStorageClientProtocol,
)
from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .error import ExperimentArtifactsNotAccessibleError


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ExperimentArtifactsServiceProtocol(Protocol):
    async def get_project_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO: ...

    async def upload_and_log_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        file: UploadFile,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> ArtifactsInfoLogArtifactResponseDTO: ...

    async def download_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes: ...

    async def delete_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO: ...

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...


class NoOpExperimentArtifactsService:
    async def get_project_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        return ArtifactsInfoResultDTO(data=[])

    async def upload_and_log_experiment_artifact(
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

    async def download_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)


class ExperimentArtifactsService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClientProtocol,
        artifacts_info_client: ArtifactsInfoClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self._object_storage = object_storage_client
        self._artifacts_info = artifacts_info_client
        self._permission_checker = permission_checker
        self._experiment_repository = experiment_repository

    async def _ensure_log_permission(
        self, user: UserProtocol, experiment_id: UUID
    ) -> UUID:
        experiment = await self._experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self._permission_checker.can_log_artifact(user.id, project_id):
            raise ExperimentArtifactsNotAccessibleError(
                f"You are not allowed to log artifacts in project {project_id}"
            )
        return project_id

    async def _ensure_view_permission(
        self, user: UserProtocol, experiment_id: UUID
    ) -> UUID:
        experiment = await self._experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self._permission_checker.can_view_artifact(user.id, project_id):
            raise ExperimentArtifactsNotAccessibleError(
                f"You are not allowed to view artifacts in project {project_id}"
            )
        return project_id

    async def _ensure_project_view_permission(
        self, user: UserProtocol, project_id: UUID
    ) -> None:
        if not await self._permission_checker.can_view_artifact(user.id, project_id):
            raise ExperimentArtifactsNotAccessibleError(
                f"You are not allowed to view artifacts in project {project_id}"
            )

    async def get_project_artifacts(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        await self._ensure_project_view_permission(user, project_id)
        return await self._artifacts_info.get_artifacts(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            start_time=start_time,
            end_time=end_time,
        )

    async def upload_and_log_experiment_artifact(
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
        """Upload and log an experiment artifact to the object storage.
        This method uploads the artifact to the object storage and logs the metadata to the scalars service.
        The artifact is logged to the scalars service with the following metadata:
        - filename: The name of the artifact.
        - content_type: The content type of the artifact.
        - size_bytes: The size of the artifact.
        - path: The path of the artifact in the object storage.
        - step: The step of the artifact.
        - metadata: The metadata of the artifact.
        - tags: The tags of the artifact.

        The artifact is uploaded to the object storage with the following metadata:
        - content: The content of the artifact.

        Args:
            user: The user.
            experiment_id: The ID of the experiment.
            file: The upload file.
            name: The name of the artifact.
            artifact_type: The type of the artifact.
            step: The step of the artifact.
            metadata: The metadata of the artifact.
            tags: The tags of the artifact.

        Returns:
            The response from the scalars service.
        """
        project_id = await self._ensure_log_permission(user, experiment_id)
        # Log the artifact to the object storage
        upload_result = await self._object_storage.upload_experiment_artifact(
            experiment_id, file
        )
        path = upload_result.path
        size = upload_result.size

        payload_metadata: dict[str, str] = {
            "filename": file.filename or f"{name}_{step}",
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": str(size),
        }
        if metadata:
            payload_metadata.update(metadata)

        payload = ArtifactsInfoLogArtifactRequestDTO(
            name=name,
            artifact_type=artifact_type,
            path=path,
            step=step,
            metadata=payload_metadata,
            tags=tags or [],
        )
        # Log the info to scalars service
        result = await self._artifacts_info.log_artifact(
            project_id, experiment_id, payload
        )
        return result

    async def download_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes:
        await self._ensure_view_permission(user, experiment_id)
        response = await self._object_storage.download_experiment_artifact(
            experiment_id, path
        )
        return response.content

    async def delete_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifact(
            experiment_id, path
        )

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifacts(experiment_id)
