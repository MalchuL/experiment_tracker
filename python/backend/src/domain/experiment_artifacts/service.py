"""Experiment artifacts service: upload, log, download, delete via object storage."""

from __future__ import annotations

import os
from typing import Any
import tempfile
import zipfile
from uuid import UUID, uuid4

from fastapi import UploadFile
from fastapi_users.models import UserProtocol
import httpx

from clients.artifacts_info import (
    ArtifactInfoEntryDTO,
    ArtifactType,
    ArtifactsInfoClientProtocol,
    ArtifactsInfoResultDTO,
    LogArtifactRequestDTO as ArtifactsInfoLogArtifactRequestDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ExperimentTrackedArtifactInfoDTO,
    ExperimentTrackedArtifactItemDTO,
    ObjectStorageClientProtocol,
)
from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from lib.logger import logger
from lib.pagination import ListOptions

from .dto import (
    ExperimentArtifactDownloadDTO,
    ExperimentArtifactDTO,
    ExperimentArtifactListResponseDTO,
)
from .error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactAmbiguousError,
    ExperimentArtifactNotFoundError,
)
from .mapper import ExperimentArtifactsMapper


def _as_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class ExperimentArtifactsService:
    """Experiment-scoped files: tracked/named blobs and step-logged artifacts (object storage + artifacts_info)."""

    def __init__(
        self,
        object_storage_client: ObjectStorageClientProtocol,
        artifacts_info_at_step_client: ArtifactsInfoClientProtocol,
        permission_checker: PermissionChecker,
        experiment_repository: ExperimentRepository,
    ):
        self._object_storage = object_storage_client
        self._artifacts_info_at_step_client = artifacts_info_at_step_client
        self._permission_checker = permission_checker
        self._experiment_repository = experiment_repository
        self._mapper = ExperimentArtifactsMapper()

    @staticmethod
    def _tracked_upload_metadata(name: str, file: UploadFile) -> dict[str, Any]:
        """Build blob ``metadata`` for tracked upload; ``name`` falls back to upload basename."""

        label = (name or "").strip()
        if not label:
            label = os.path.basename(file.filename or "") or uuid4().hex
        return {"name": label}

    async def _list_all_tracked_experiment_artifacts(
        self, project_id: UUID, experiment_id: UUID
    ) -> list[ExperimentTrackedArtifactItemDTO]:
        """
        List all tracked experiment artifacts for an experiment in the project.
        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment.
        Returns:
            A list of ExperimentTrackedArtifactItemDTO objects representing the artifacts.
        """
        out: list[ExperimentTrackedArtifactItemDTO] = []
        offset = 0
        limit = 100
        while True:
            batch = await self._object_storage.list_experiment_tracked_artifacts(
                project_id,
                experiment_id,
                limit=limit,
                offset=offset,
            )
            out.extend(batch.data)
            if not batch.has_next:
                break
            offset += batch.size
        return out

    def _normalize_filepath(self, filepath: str) -> str:
        """Normalize a filepath to a relative path.

        Removes any ``..``, ``:``, unsafe characters, replaces backslashes with ``/``,
        and ensures the path is relative.

        Args:
            filepath: The filepath to normalize.

        Returns:
            The normalized filepath.
        """
        return self._mapper.normalize_relative_filepath(filepath)

    async def _find_tracked_artifact(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentTrackedArtifactInfoDTO | None:
        """
        Find a tracked artifact by filepath, blob_id, or artifact_hash (only one of them is required).
        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment.
            filepath: The filepath of the artifact.
            blob_id: The blob_id of the artifact.
            artifact_hash: The artifact_hash of the artifact.
        Returns:
            The ExperimentTrackedArtifactInfoDTO object representing the artifact.
        """
        if filepath is None and blob_id is None and artifact_hash is None:
            raise ValueError(
                "At least one identifier is required: filepath, blob_id, or artifact_hash"
            )
        try:
            return await self._object_storage.get_experiment_tracked_artifact_info(
                project_id,
                experiment_id,
                file_path=filepath,
                blob_id=blob_id,
                artifact_hash=artifact_hash,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

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

    @staticmethod
    def _pick_single_logged_entry(
        result: ArtifactsInfoResultDTO,
        experiment_id: UUID,
        step: int,
        name: str,
        artifact_type: ArtifactType | None,
    ) -> ArtifactInfoEntryDTO:
        """
        Pick a single logged entry from the result that matches the step, name and artifact_type.
        Args:
            result: The result from the artifacts info at step client (usually from scalars service).
            experiment_id: The ID of the experiment.
            step: The step of the artifact.
            name: The name of the artifact.
            artifact_type: The type of the artifact.
        Returns:
            The ArtifactInfoEntryDTO object representing the artifact.
        """
        entries: list[ArtifactInfoEntryDTO] = []
        for group in result.data:
            if group.experiment_id != experiment_id:
                continue
            for entry in group.artifacts_info:
                if entry.step != step or entry.name != name:
                    continue
                if artifact_type is not None and entry.artifact_type != artifact_type:
                    continue
                entries.append(entry)
        unique_paths = list(dict.fromkeys(e.path for e in entries))
        if not unique_paths:
            detail = f"No artifact logged for experiment {experiment_id} at step={step} name={name!r}"
            if artifact_type is not None:
                detail += f" artifact_type={artifact_type!r}"
            raise ExperimentArtifactNotFoundError(detail)
        if len(unique_paths) > 1:
            logger.warning(
                f"Multiple stored blobs match this step and name; pass artifact_type to disambiguate. "
                f"Experiment: {experiment_id}, Step: {step}, Name: {name}, Artifact Type: {artifact_type}"
            )
            raise ExperimentArtifactAmbiguousError(
                "Multiple stored blobs match this step and name; pass artifact_type to disambiguate."
            )
        blob_hash = unique_paths[0]
        return next(e for e in entries if e.path == blob_hash)

    @staticmethod
    def _get_response_fields_for_download_at_step(
        entry: ArtifactInfoEntryDTO, name: str, step: int
    ) -> tuple[str, str]:
        """Get the filename and content type from the entry.
        Args:
            entry: The entry from the artifacts info at step client.
            name: The name of the artifact.
            step: The step of the artifact.
        Returns:
            A tuple containing the filename and content type.
        """
        meta = entry.metadata or {}
        filename = (meta.get("filename") or "").strip() or f"{name}_{step}"
        content_type = (
            meta.get("content_type") or ""
        ).strip() or "application/octet-stream"
        return filename, content_type

    # Tracked artifacts for experiment

    async def list_experiment_artifacts(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        list_options: ListOptions = ListOptions(),
        file_paths: list[str] | None = None,
    ) -> ExperimentArtifactListResponseDTO:
        """
        List all tracked artifacts for an experiment.

        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            file_paths: Optional list of stored ``file_path`` values to filter by (exact match).

        Returns:
            A list of ExperimentArtifactDTO objects representing the artifacts. Each object contains:
            - id: The unique identifier of the artifact.
            - hash: The hash of the artifact.
            - file_path: The path of the artifact.
            - mime_type: The MIME type of the artifact.
            - size: The size of the artifact in bytes.
        """
        project_id = await self._ensure_view_permission(user, experiment_id)
        upstream_page = await self._object_storage.list_experiment_tracked_artifacts(
            project_id,
            experiment_id,
            limit=list_options.limit,
            offset=list_options.offset,
            file_paths=file_paths,
        )
        return ExperimentArtifactListResponseDTO(
            data=[
                self._mapper.tracked_item_to_dto(experiment_id, item)
                for item in upstream_page.data
            ],
            has_next=upstream_page.has_next,
            size=upstream_page.size,
            total=upstream_page.total,
        )

    async def upsert_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str | None,
        filepath: str,
        file: UploadFile,
    ) -> ExperimentArtifactDTO:
        """Upsert an artifact for an experiment.
        Upserts an artifact for an experiment. If the artifact already exists, it is deleted and a new one is uploaded.
        The artifact is stored as a tracked artifact in the object storage.
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            name: The name of the artifact.
            filepath: The filepath of the artifact (relative to the experiment root).
            file: The file to upload.
        Returns:
            The ExperimentArtifactDTO object representing the upserted artifact.
        """
        project_id = await self._ensure_log_permission(user, experiment_id)
        tracked_path = self._normalize_filepath(filepath)
        existing = await self._find_tracked_artifact(
            project_id, experiment_id, filepath=tracked_path
        )
        if existing is not None:
            await self._object_storage.delete_experiment_artifact(
                project_id, experiment_id, existing.hash
            )
        upload_result = await self._object_storage.upload_experiment_tracked(
            project_id,
            experiment_id,
            file,
            artifact_hash=None,  # Content hash will be computed by object storage
            file_path=tracked_path,
            metadata=self._tracked_upload_metadata(name or "", file),
        )
        return self._mapper.tracked_upload_to_dto(
            experiment_id, upload_result, file.filename
        )

    async def get_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDTO:
        """Get an artifact by filepath, blob_id, or artifact_hash (only one of them is required).
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            filepath: The filepath of the artifact (relative to the experiment root).
            blob_id: The blob_id of the artifact.
            artifact_hash: The artifact_hash of the artifact.
        Returns:
            The ExperimentArtifactDTO object representing the artifact.
        """
        if filepath is None and blob_id is None and artifact_hash is None:
            raise ValueError(
                "At least one identifier is required: filepath, blob_id, or artifact_hash"
            )
        project_id = await self._ensure_view_permission(user, experiment_id)
        tracked_path = self._normalize_filepath(filepath) if filepath else None
        item = await self._find_tracked_artifact(
            project_id,
            experiment_id,
            filepath=tracked_path,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        if item is None:
            raise ExperimentArtifactNotFoundError(
                f"Artifact not found for filepath={filepath}, blob_id={blob_id}, artifact_hash={artifact_hash}"
            )
        return self._mapper.tracked_info_to_dto(experiment_id, item)

    async def download_experiment_artifact(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        filepath: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ExperimentArtifactDownloadDTO:
        """
        Download an artifact by filepath, blob_id, or artifact_hash (only one of them is required).
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            filepath: The filepath of the artifact (relative to the experiment root).
            blob_id: The blob_id of the artifact.
            artifact_hash: The artifact_hash of the artifact.
        Returns:
            Bytes and display metadata for the response.
        """
        if filepath is None and blob_id is None and artifact_hash is None:
            raise ValueError(
                "At least one identifier is required: filepath, blob_id, or artifact_hash"
            )
        project_id = await self._ensure_view_permission(user, experiment_id)
        tracked_path = self._normalize_filepath(filepath) if filepath else None
        item = await self._find_tracked_artifact(
            project_id,
            experiment_id,
            filepath=tracked_path,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        if item is None:
            raise ExperimentArtifactNotFoundError(
                f"Artifact not found for filepath={filepath}, blob_id={blob_id}, artifact_hash={artifact_hash}"
            )
        response = await self._object_storage.download_experiment_artifact(
            project_id,
            experiment_id,
            item.hash,
            tracked=True,
        )
        filename = os.path.basename(item.file_path) or "artifact"
        return ExperimentArtifactDownloadDTO(
            content=response.content,
            filename=filename,
            content_type=item.mime_type,
        )

    # TODO: Check it (does it work?)
    async def download_experiment_artifacts_archive(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        name: str,
    ) -> tuple[str, str]:
        project_id = await self._ensure_view_permission(user, experiment_id)
        safe_name = self._mapper.validate_artifact_name(name)
        items = [
            i
            for i in await self._list_all_tracked_experiment_artifacts(
                project_id, experiment_id
            )
            if (i.metadata or {}).get("name") == safe_name
        ]
        if not items:
            raise ExperimentArtifactNotFoundError(f"No artifacts found for name={name}")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        archive_path = tmp.name
        tmp.close()
        try:
            with zipfile.ZipFile(
                archive_path, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                for item in items:
                    arcname = item.file_path or os.path.basename(item.file_path)
                    response = await self._object_storage.download_experiment_artifact(
                        project_id,
                        experiment_id,
                        item.hash,
                        tracked=True,
                    )
                    zipf.writestr(arcname, response.content)
            return archive_path, f"{name}.zip"
        except Exception:
            if os.path.exists(archive_path):
                os.remove(archive_path)
            raise

    # Artifacts at steps

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
        """
        Upload and log an artifact at a step.
        Uploads an untracked artifact to the object storage. Info stored inside scalars service.
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            file: The file to upload.
            name: The name of the artifact.
            artifact_type: The type of the artifact.
            step: The step of the artifact.
            metadata: The metadata of the artifact.
            tags: The tags of the artifact.
        Returns:
            The ArtifactsInfoLogArtifactResponseDTO object representing the logged artifact.
        """
        project_id = await self._ensure_log_permission(user, experiment_id)

        upload_result = await self._object_storage.upload_experiment_untracked(
            project_id,
            experiment_id,
            file,
            artifact_hash=None,  # Content hash will be computed by object storage
        )
        artifact_hash = upload_result.hash
        size = upload_result.size

        payload_metadata: dict[str, str] = {
            "filename": file.filename or f"{name}_{step}",
            # We put content type in metadata to be able to display it in the UI
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": str(size),
        }
        if metadata:
            payload_metadata.update(metadata)

        payload = ArtifactsInfoLogArtifactRequestDTO(
            name=name,
            artifact_type=artifact_type,
            path=artifact_hash,  # Path is the artifact hash
            step=step,
            metadata=payload_metadata,
            tags=tags or [],
        )
        return await self._artifacts_info_at_step_client.log_artifact_at_step(
            project_id, experiment_id, payload
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
        """Get the artifacts info at steps for a project, experiment, artifact type, name, step, start time and end time.
        Args:
            user: The user making the request.
            project_id: The ID of the project.
            experiment_ids: The IDs of the experiments.
            artifact_types: The types of the artifacts.
            artifact_names: The names of the artifacts.
            steps: The steps of the artifacts.
            start_time: The start time of the artifacts.
            end_time: The end time of the artifacts.
        Returns:
            The ArtifactsInfoResultDTO object representing the artifacts info.
        """
        await self._ensure_project_view_permission(user, project_id)
        result = await self._artifacts_info_at_step_client.get_artifacts(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            steps=steps,
            limit=list_options.limit,
            offset=list_options.offset,
            start_time=start_time,
            end_time=end_time,
        )
        return result

    async def download_experiment_artifact_at_step(
        self,
        user: UserProtocol,
        experiment_id: UUID,
        step: int,
        name: str,
        artifact_type: ArtifactType | None = None,
    ) -> ExperimentArtifactDownloadDTO:
        """Download an artifact at a step.
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            step: The step of the artifact.
            name: The name of the artifact.
            artifact_type: The type of the artifact.
        Returns:
            The downloaded artifact payload and display metadata.
        """
        project_id = await self._ensure_view_permission(user, experiment_id)
        result = await self._artifacts_info_at_step_client.get_artifacts(
            project_id=project_id,
            experiment_ids=[experiment_id],
            artifact_names=[name],
            artifact_types=[artifact_type] if artifact_type else None,
            steps=[step],
        )
        entry = self._pick_single_logged_entry(
            result, experiment_id, step, name, artifact_type
        )
        filename, content_type = self._get_response_fields_for_download_at_step(
            entry, name, step
        )
        response = await self._object_storage.download_experiment_artifact(
            project_id,
            experiment_id,
            artifact_hash=entry.path,
            tracked=False,
        )
        return ExperimentArtifactDownloadDTO(
            content=response.content,
            filename=filename,
            content_type=content_type,
        )

    # For both tracked and untracked artifacts
    async def delete_experiment_artifact_by_hash(
        self, user: UserProtocol, experiment_id: UUID, hash: str
    ) -> DeleteExperimentArtifactResponseDTO:
        """Delete an artifact (tracked or untracked) by hash (path inside object storage).
        Args:
            user: The user making the request.
            experiment_id: The ID of the experiment.
            hash: The hash of the artifact (path inside object storage).
        Returns:
            The DeleteExperimentArtifactResponseDTO object representing the deleted artifact.
        """
        project_id = await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_experiment_artifact(
            project_id, experiment_id, hash
        )

    async def delete_experiment_all_artifacts(
        self, user: UserProtocol, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        """Delete all (tracked and untracked) artifacts for an experiment."""
        project_id = await self._ensure_log_permission(user, experiment_id)
        return await self._object_storage.delete_all_experiment_artifacts(
            project_id, experiment_id
        )
