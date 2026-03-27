"""Experiment artifacts service: upload, log, download, delete."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import PurePosixPath
from urllib.parse import quote
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
from models import ExperimentArtifact
from domain.rbac.wrapper import PermissionChecker
from fastapi_users.models import UserProtocol

from .dto import (
    ExperimentArtifactDTO,
    ExperimentArtifactsDeleteResponseDTO,
)
from .error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactNotFoundError,
)
from .repository import ExperimentArtifactRepository


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ExperimentArtifactsServiceProtocol(Protocol):
    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        names: list[str] | None = None,
    ) -> list[ExperimentArtifactDTO]: ...

    async def get_project_artifacts_at_step(
        self,
        user: UserProtocol,
        project_id: UUID,
        experiment_ids: list[UUID] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ArtifactsInfoResultDTO: ...

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
    ) -> ArtifactsInfoLogArtifactResponseDTO: ...

    async def download_experiment_artifact_at_step(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes: ...

    async def delete_experiment_artifact_at_step(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO: ...

    async def delete_experiment_artifacts_at_step(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO: ...

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO: ...

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> ExperimentArtifactDTO: ...

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> tuple[bytes, str, str]: ...

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]: ...

    async def delete_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str | None = None,
    ) -> ExperimentArtifactsDeleteResponseDTO: ...


class NoOpExperimentArtifactsService:
    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        names: list[str] | None = None,
    ) -> list[ExperimentArtifactDTO]:
        return []

    async def get_project_artifacts_at_step(
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
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifact_at_step(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        return DeleteExperimentArtifactResponseDTO(deleted=True)

    async def delete_experiment_artifacts_at_step(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=0)

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> ExperimentArtifactDTO:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> tuple[bytes, str, str]:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        raise ExperimentArtifactsNotAccessibleError("Experiment artifacts unavailable")

    async def delete_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str | None = None,
    ) -> ExperimentArtifactsDeleteResponseDTO:
        return ExperimentArtifactsDeleteResponseDTO(deleted_count=0)


class ExperimentArtifactsService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClientProtocol,
        artifacts_info_at_step_client: ArtifactsInfoClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
        artifact_repository: ExperimentArtifactRepository,
    ):
        self._object_storage = object_storage_client
        self._artifacts_info_at_step_client = artifacts_info_at_step_client
        self._permission_checker = permission_checker
        self._experiment_repository = experiment_repository
        self._artifacts_info_repository = artifact_repository

    def _normalize_relative_filepath(self, filepath: str) -> str:
        normalized = filepath.strip().replace("\\", "/")
        pure_path = PurePosixPath(normalized)
        if (
            not normalized
            or normalized.startswith("/")
            or ".." in pure_path.parts
            or ":" in normalized
        ):
            raise ValueError(
                "Invalid filepath. It must be relative, non-empty, "
                "must not contain '..', ':' or start with '/'."
            )
        return normalized

    def _build_storage_path(self, name: str, filepath: str) -> str:
        normalized_filepath = self._normalize_relative_filepath(filepath)
        encoded_segments = [quote(part, safe="") for part in normalized_filepath.split("/")]
        encoded_name = quote(name.strip(), safe="")
        return f"named/{encoded_name}/{'/'.join(encoded_segments)}"

    def _to_artifact_dto(
        self, artifact: ExperimentArtifact
    ) -> ExperimentArtifactDTO:
        return ExperimentArtifactDTO(
            id=artifact.id,
            experiment_id=artifact.experiment_id,
            name=artifact.name,
            filepath=artifact.filepath,
            filename=artifact.filename,
            mime_type=artifact.mime_type,
            storage_path=artifact.storage_path,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

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

    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        names: list[str] | None = None,
    ) -> list[ExperimentArtifactDTO]:
        await self._ensure_view_permission(user, experiment_id)
        artifacts = await self._artifacts_info_repository.list_by_experiment(
            experiment_id, names
        )
        return [self._to_artifact_dto(artifact) for artifact in artifacts]

    async def get_project_artifacts_at_step(
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
        return await self._artifacts_info_at_step_client.get_artifacts(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            start_time=start_time,
            end_time=end_time,
        )

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
        result = await self._artifacts_info_at_step_client.log_artifact_at_step(
            project_id, experiment_id, payload
        )
        return result

    async def download_experiment_artifact_at_step(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> bytes:
        await self._ensure_view_permission(user, experiment_id)
        response = await self._object_storage.download_experiment_artifact(
            experiment_id, path
        )
        return response.content

    async def delete_experiment_artifact_at_step(
        self, user: UserProtocol, experiment_id: UUID, path: str
    ) -> DeleteExperimentArtifactResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifact(
            experiment_id, path
        )

    async def delete_experiment_artifacts_at_step(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifacts(experiment_id)

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO:
        await self._ensure_log_permission(user, experiment_id)
        normalized_filepath = self._normalize_relative_filepath(filepath)
        storage_path = self._build_storage_path(name, normalized_filepath)
        existing = await self._artifacts_info_repository.get_by_identity(
            experiment_id, name, normalized_filepath
        )

        uploaded_path: str | None = None
        try:
            if existing is not None:
                await self._object_storage.delete_experiment_artifact(
                    experiment_id, existing.storage_path
                )
            upload_result = await self._object_storage.upload_experiment_artifact(
                experiment_id, file, path=storage_path
            )
            uploaded_path = upload_result.path
            filename = file.filename or os.path.basename(normalized_filepath) or name
            mime_type = file.content_type or "application/octet-stream"

            if existing is not None:
                artifact = await self._artifacts_info_repository.update(
                    existing.id,
                    filename=filename,
                    mime_type=mime_type,
                    storage_path=uploaded_path,
                )
            else:
                artifact = ExperimentArtifact(
                    experiment_id=experiment_id,
                    name=name,
                    filepath=normalized_filepath,
                    filename=filename,
                    mime_type=mime_type,
                    storage_path=uploaded_path,
                )
                artifact = await self._artifacts_info_repository.create(artifact)
            await self._artifacts_info_repository.commit()
            return self._to_artifact_dto(artifact)
        except Exception:
            await self._artifacts_info_repository.rollback()
            if uploaded_path is not None:
                try:
                    await self._object_storage.delete_experiment_artifact(
                        experiment_id, uploaded_path
                    )
                except Exception:
                    pass
            raise

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> ExperimentArtifactDTO:
        await self._ensure_view_permission(user, experiment_id)
        normalized_filepath = self._normalize_relative_filepath(filepath)
        artifact = await self._artifacts_info_repository.get_by_identity(
            experiment_id, name, normalized_filepath
        )
        if artifact is None:
            raise ExperimentArtifactNotFoundError(
                f"Artifact not found for name={name}, filepath={normalized_filepath}"
            )
        return self._to_artifact_dto(artifact)

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> tuple[bytes, str, str]:
        artifact = await self.get_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
        )
        response = await self._object_storage.download_experiment_artifact(
            experiment_id, artifact.storage_path
        )
        return response.content, artifact.mime_type, artifact.filename

    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        await self._ensure_view_permission(user, experiment_id)
        artifacts = await self._artifacts_info_repository.list_by_name(experiment_id, name)
        if not artifacts:
            raise ExperimentArtifactNotFoundError(
                f"No artifacts found for name={name}"
            )

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        archive_path = tmp.name
        tmp.close()
        try:
            with zipfile.ZipFile(
                archive_path, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                for artifact in artifacts:
                    response = await self._object_storage.download_experiment_artifact(
                        experiment_id, artifact.storage_path
                    )
                    zipf.writestr(artifact.filepath, response.content)
            return archive_path, f"{name}.zip"
        except Exception:
            if os.path.exists(archive_path):
                os.remove(archive_path)
            raise

    async def delete_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
        filepath: str | None = None,
    ) -> ExperimentArtifactsDeleteResponseDTO:
        await self._ensure_log_permission(user, experiment_id)
        if filepath is not None:
            normalized_filepath = self._normalize_relative_filepath(filepath)
            artifact = await self._artifacts_info_repository.get_by_identity(
                experiment_id, name, normalized_filepath
            )
            if artifact is None:
                return ExperimentArtifactsDeleteResponseDTO(deleted_count=0)
            await self._object_storage.delete_experiment_artifact(
                experiment_id, artifact.storage_path
            )
            deleted_count = await self._artifacts_info_repository.delete_by_identity(
                experiment_id, name, normalized_filepath
            )
            await self._artifacts_info_repository.commit()
            return ExperimentArtifactsDeleteResponseDTO(deleted_count=deleted_count)

        artifacts = await self._artifacts_info_repository.list_by_name(experiment_id, name)
        if not artifacts:
            return ExperimentArtifactsDeleteResponseDTO(deleted_count=0)
        for artifact in artifacts:
            await self._object_storage.delete_experiment_artifact(
                experiment_id, artifact.storage_path
            )
        deleted_count = await self._artifacts_info_repository.delete_by_name(
            experiment_id, name
        )
        await self._artifacts_info_repository.commit()
        return ExperimentArtifactsDeleteResponseDTO(deleted_count=deleted_count)
