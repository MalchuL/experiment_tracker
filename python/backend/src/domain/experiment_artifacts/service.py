"""Experiment artifacts service: upload, log, download, delete."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from fastapi import UploadFile

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from clients.artifacts_info_client import ArtifactsInfoClientProtocol
from clients.object_storage_client import ObjectStorageClient
from .dto import LogArtifactRequestDTO, LogArtifactResponseDTO
from .error import ExperimentArtifactsNotAccessibleError


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ExperimentArtifactsServiceProtocol(Protocol):
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
    ) -> LogArtifactResponseDTO: ...

    async def log_artifact(
        self, user: UserProtocol, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO: ...

    async def download_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes: ...

    async def delete_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> dict[str, Any]: ...

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> dict[str, Any]: ...


class NoOpExperimentArtifactsService:
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
    ) -> LogArtifactResponseDTO:
        return LogArtifactResponseDTO(status="logged")

    async def log_artifact(
        self, user: UserProtocol, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO:
        return LogArtifactResponseDTO(status="logged")

    async def download_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> dict[str, Any]:
        return {"deleted": True}

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> dict[str, Any]:
        return {"deleted_count": 0}


class ExperimentArtifactsService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClient,
        artifacts_info_client: ArtifactsInfoClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self._object_storage = object_storage_client
        self._artifacts_info = artifacts_info_client
        self._permission_checker = permission_checker
        self._experiment_repository = experiment_repository

    async def _ensure_log_permission(self, user: UserProtocol, experiment_id: UUID) -> UUID:
        experiment = await self._experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self._permission_checker.can_log_artifact(user.id, project_id):
            raise ExperimentArtifactsNotAccessibleError(
                f"You are not allowed to log artifacts in project {project_id}"
            )
        return project_id

    async def _ensure_view_permission(self, user: UserProtocol, experiment_id: UUID) -> UUID:
        experiment = await self._experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        if not await self._permission_checker.can_view_artifact(user.id, project_id):
            raise ExperimentArtifactsNotAccessibleError(
                f"You are not allowed to view artifacts in project {project_id}"
            )
        return project_id

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
    ) -> LogArtifactResponseDTO:
        project_id = await self._ensure_log_permission(user, experiment_id)
        upload_result = await self._object_storage.upload_experiment_artifact(
            experiment_id, file
        )
        path = upload_result.get("path", "")
        size = upload_result.get("size", 0)

        payload_metadata: dict[str, str] = {
            "filename": file.filename or f"{name}_{step}",
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": str(size),
        }
        if metadata:
            payload_metadata.update(metadata)

        payload = LogArtifactRequestDTO(
            name=name,
            artifact_type=artifact_type,
            path=path,
            step=step,
            metadata=payload_metadata,
            tags=tags or [],
        )
        result = await self._artifacts_info.log_artifact(
            project_id, experiment_id, payload.model_dump()
        )
        return LogArtifactResponseDTO.model_validate(result)

    async def log_artifact(
        self, user: UserProtocol, experiment_id: UUID, payload: LogArtifactRequestDTO
    ) -> LogArtifactResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        experiment = await self._experiment_repository.get_by_id(experiment_id)
        project_id = _as_uuid(experiment.project_id)
        result = await self._artifacts_info.log_artifact(
            project_id, experiment_id, payload.model_dump()
        )
        return LogArtifactResponseDTO.model_validate(result)

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
    ) -> dict[str, Any]:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifact(
            experiment_id, path
        )

    async def delete_experiment_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> dict[str, Any]:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifacts(experiment_id)
