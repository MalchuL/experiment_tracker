"""Business logic for experiment-scoped artifacts storage."""

from __future__ import annotations

import os
import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from object_storage.domain.experiment_artifacts_storage.error import (
    HashNotValidError,
)
from object_storage.logger import logger
from object_storage.db.models import ExperimentBlob

from .mapper import ArtifactsStorageMapper
from .dto import (
    ArtifactStreamResponseDTO,
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ExperimentArtifactsUsageItemDTO,
    ExperimentArtifactsUsageResponseDTO,
    TrackedArtifactsListResponseDTO,
    TrackedArtifactInfoResponseDTO,
    TrackedUploadArtifactResponseDTO,
    UntrackedUploadArtifactResponseDTO,
)
from object_storage.domain.buckets.service import BucketRegistryService
from object_storage.domain.experiment_artifacts_storage.repository import (
    ExperimentArtifactsRepository,
)
from object_storage.utils.filepath import normalize_path, validate_relative_path


class ArtifactsStorageService:
    """Store and manage non-deduplicated artifacts per experiment."""

    def __init__(
        self,
        buckets_service: BucketRegistryService,
        artifacts_repository: ExperimentArtifactsRepository,
    ) -> None:
        """Initialize experiment artifacts service dependencies.

        Args:
            buckets_service: Bucket registry service used for object operations.
            artifacts_repository: Repository for tracked experiment artifact metadata.
        """

        self._buckets_service = buckets_service
        self._artifacts_repository = artifacts_repository
        self._mapper = ArtifactsStorageMapper()

    def _remove_orphan_object_after_failed_upload(
        self, bucket_name: str, blob_hash: str
    ) -> None:
        """Delete S3/MinIO object after DB rollback; ignores errors (best-effort)."""

        try:
            self._buckets_service.storage.delete_blob(bucket_name, blob_hash)
        except Exception:
            logger.exception(
                "Failed to delete orphan object after failed upload",
                extra={"bucket": bucket_name, "hash": blob_hash},
            )

    def check_hash(self, hash: str) -> None:
        """Validate artifact hash format.

        Args:
            hash: Candidate object key/hash string.

        Raises:
            HashNotValidError: If value is not 4-64 hex characters.
        """

        if not re.fullmatch(r"^[0-9a-fA-F]{4,64}$", hash):
            raise HashNotValidError(
                f"Hash {hash} is not valid, must be 4-64 hex characters"
            )

    async def upload_artifact_and_forget(
        self,
        project_id: UUID,
        experiment_id: UUID,
        upload: UploadFile,
        artifact_hash: str | None = None,
    ) -> UntrackedUploadArtifactResponseDTO:
        """
        Upload one artifact under an experiment-specific prefix.
        Used to store artifact that are not part of the experiment manifest.
        Currently used to store not final data in training like image, video, etc.

        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment.
            upload: The upload file.
            artifact_hash: The hash of the artifact that used to store in storage.

        Returns:
            The response from the object storage.
            The response contains the hash and size of the uploaded artifact.
        """
        artifact_hash = artifact_hash or uuid4().hex
        self.check_hash(artifact_hash)
        bucket_name = await self._buckets_service.ensure_bucket(
            project_id, experiment_id
        )
        upload_result = await self._buckets_service.upload_blob(
            project_id, experiment_id, upload, artifact_hash
        )
        try:
            await self._buckets_service.commit()
        except Exception:
            await self._buckets_service.rollback()
            self._remove_orphan_object_after_failed_upload(
                bucket_name, upload_result.hash
            )
            raise
        return self._mapper.upload_artifact_to_untracked_response(upload_result)

    @staticmethod
    def _mime_type_for_tracked(upload: UploadFile, content_type: str | None) -> str:
        """Resolve MIME type for tracked artifact rows.

        Args:
            upload: Incoming upload object from FastAPI.
            content_type: Optional explicit MIME type override from request query.

        Returns:
            Effective MIME type, defaulting to ``application/octet-stream``.
        """

        if content_type is not None:
            stripped = content_type.strip()
            if stripped:
                return stripped
        from_upload = (upload.content_type or "").strip()
        if from_upload:
            return from_upload
        return "application/octet-stream"

    async def upload_artifact_and_track(
        self,
        project_id: UUID,
        experiment_id: UUID,
        upload: UploadFile,
        content_type: str | None = None,
        artifact_hash: str | None = None,
        file_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TrackedUploadArtifactResponseDTO:
        """
        Upload one artifact under an experiment-specific prefix.
        Used to store artifact that are part of the experiment manifest.
        Currently used to store final data in training like model, configs, data and so on.

        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment.
            upload: The upload file.
            content_type: Optional MIME type for the tracked row; when omitted or blank,
                uses the upload part's content type, then ``application/octet-stream``.
            artifact_hash: The hash of the artifact that used to store in storage.
            file_path: Relative path for the tracked blob (stored on the row).
            metadata: Optional JSON object stored as-is on the blob row (default ``{}``).

        Returns:
            The response from the object storage.
            The response contains the hash and size of the uploaded artifact.
        """
        artifact_hash = artifact_hash or uuid4().hex
        self.check_hash(artifact_hash)

        bucket_name = await self._buckets_service.ensure_bucket(
            project_id, experiment_id
        )
        upload_result = await self._buckets_service.upload_blob(
            project_id, experiment_id, upload, artifact_hash
        )

        try:
            stored_rel_path = normalize_path(
                file_path or upload.filename or artifact_hash
            )
            if not validate_relative_path(stored_rel_path):
                raise ValueError(f"Invalid file path: {stored_rel_path}")
            model_blob = await self._artifacts_repository.create_experiment_blob(
                ExperimentBlob(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    artifact_hash=upload_result.hash,
                    file_path=stored_rel_path,
                    mime_type=self._mime_type_for_tracked(upload, content_type),
                    size=upload_result.size,
                    artifact_metadata=dict(metadata or {}),
                )
            )

            await self._artifacts_repository.commit()
        except IntegrityError as exc:
            await self._artifacts_repository.rollback()
            self._remove_orphan_object_after_failed_upload(
                bucket_name, upload_result.hash
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to persist experiment artifact metadata",
            ) from exc
        except Exception:
            await self._artifacts_repository.rollback()
            self._remove_orphan_object_after_failed_upload(
                bucket_name, upload_result.hash
            )
            raise

        return self._mapper.experiment_model_to_tracked_response(model_blob)

    async def list_artifacts(
        self,
        project_id: UUID,
        experiment_id: UUID,
        limit: int = 100,
        offset: int = 0,
        file_paths: list[str] | None = None,
    ) -> TrackedArtifactsListResponseDTO:
        """List tracked artifacts for one experiment with pagination metadata.

        Args:
            project_id: Project UUID owning the experiment.
            experiment_id: Experiment UUID to list artifacts for.
            limit: Maximum number of rows to return.
            offset: Pagination offset.
            file_paths: Optional path filters; only matching tracked rows are returned.

        Returns:
            Paginated tracked artifacts response DTO.
        """

        blobs, total = await self._artifacts_repository.list_experiment_blobs(
            project_id,
            experiment_id,
            limit,
            offset,
            file_paths=file_paths,
        )
        data = [
            self._mapper.experiment_model_to_tracked_response(blob) for blob in blobs
        ]
        return TrackedArtifactsListResponseDTO(
            data=data,
            has_next=offset + len(data) < total,
            size=len(data),
            total=total,
        )

    async def get_artifact_stream(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        tracked: bool = False,
    ) -> ArtifactStreamResponseDTO:
        """Get a streaming handle for one artifact.

        Args:
            project_id: Project UUID owning the artifact.
            experiment_id: Experiment UUID owning the artifact.
            artifact_hash: Object key/hash to stream.
            tracked: When ``True``, resolve metadata row and include filename/MIME info.

        Returns:
            Stream DTO with byte stream plus optional tracked metadata.

        Raises:
            ValueError: If tracked metadata is requested and row is missing.
        """
        if tracked:
            blob = await self._artifacts_repository.get_experiment_blob(
                project_id, experiment_id, artifact_hash=artifact_hash
            )
            if blob is None:
                raise ValueError(f"Artifact {artifact_hash} not found")
            blob_stream = await self._buckets_service.get_blob_stream(
                project_id, experiment_id, artifact_hash
            )
            return ArtifactStreamResponseDTO(
                stream=blob_stream,
                size=blob.size,
                mime_type=blob.mime_type,
                filename=os.path.basename(blob.file_path),
                file_path=blob.file_path,
            )
        blob_stream = await self._buckets_service.get_blob_stream(
            project_id, experiment_id, artifact_hash
        )
        return ArtifactStreamResponseDTO(
            stream=blob_stream,
            size=None,
            mime_type="application/octet-stream",
            filename=None,
            file_path=None,
        )

    async def get_tracked_artifact_info(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        file_path: str | None = None,
        blob_id: UUID | None = None,
        artifact_hash: str | None = None,
    ) -> TrackedArtifactInfoResponseDTO:
        """Get one tracked artifact metadata record.

        Args:
            project_id: Project UUID owning the artifact.
            experiment_id: Experiment UUID owning the artifact.
            file_path: Optional tracked file path filter.
            blob_id: Optional tracked row UUID filter.
            artifact_hash: Optional hash filter.

        Returns:
            Tracked artifact metadata DTO.

        Raises:
            ValueError: If no lookup identifier is provided, path is invalid, or no row exists.
        """

        if file_path is None and blob_id is None and artifact_hash is None:
            raise ValueError("file_path, blob_id, or artifact_hash is required")
        normalized_path: str | None = None
        if file_path is not None:
            normalized_path = normalize_path(file_path)
            if not validate_relative_path(normalized_path):
                raise ValueError(f"Invalid file path: {normalized_path}")
        blob = await self._artifacts_repository.get_experiment_blob(
            project_id,
            experiment_id,
            artifact_hash=artifact_hash,
            file_path=normalized_path,
            blob_id=blob_id,
        )
        if blob is None:
            raise ValueError("Tracked artifact not found")
        return self._mapper.experiment_model_to_tracked_info_response(blob)

    async def delete_artifact(
        self, project_id: UUID, experiment_id: UUID, artifact_hash: str
    ) -> DeleteArtifactResponseDTO:
        """Delete one artifact for an experiment (tracked metadata and stored object).

        Args:
            project_id: Project UUID owning the artifact.
            experiment_id: Experiment UUID owning the artifact.
            artifact_hash: Artifact hash/object key to remove.

        Returns:
            DTO indicating the delete operation completed.
        """
        # Delete the artifact from the database (if not tracked just skipped)
        await self._artifacts_repository.delete_experiment_blob(
            project_id, experiment_id, artifact_hash
        )
        await self._buckets_service.delete_blob(
            project_id, experiment_id, artifact_hash
        )
        await self._artifacts_repository.commit()
        return self._mapper.delete_artifact_to_response(True)

    async def delete_experiment(
        self, project_id: UUID, experiment_id: UUID
    ) -> DeleteExperimentArtifactsResponseDTO:
        """Delete all artifacts that belong to an experiment."""

        await self._buckets_service.delete_bucket(project_id, experiment_id)
        await self._artifacts_repository.delete_all_experiment_blobs(
            project_id, experiment_id
        )
        await self._artifacts_repository.commit()
        return self._mapper.delete_experiment_to_response(deleted_count=-1)

    async def get_experiment_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> ExperimentArtifactsUsageResponseDTO:
        """Aggregate usage for one experiment across tracked and at-step artifacts.

        Args:
            project_id: Project UUID owning the experiment.
            experiment_id: Experiment UUID to aggregate usage for.

        Returns:
            Typed usage payload with tracked totals, at-step estimates, and bucket bytes.
        """

        tracked = await self._artifacts_repository.get_experiment_blob_usage(
            project_id, experiment_id
        )
        bucket_name = await self._buckets_service.get_bucket_name(
            project_id, experiment_id
        )
        bucket_bytes = 0
        object_count = 0
        if bucket_name and self._buckets_service.storage.bucket_exists(bucket_name):
            entries = self._buckets_service.storage.list_blob_entries(bucket_name)
            object_count = len(entries)
            bucket_bytes = sum(e.size for e in entries)
        at_step_bytes = max(0, bucket_bytes - tracked["bytes"])
        at_step_count = max(0, object_count - tracked["count"])
        return ExperimentArtifactsUsageResponseDTO(
            project_id=str(project_id),
            experiment_id=str(experiment_id),
            experiment_artifacts=ExperimentArtifactsUsageItemDTO(
                count=int(tracked["count"]),
                bytes=int(tracked["bytes"]),
            ),
            at_step_artifacts=ExperimentArtifactsUsageItemDTO(
                count=at_step_count,
                bytes=at_step_bytes,
            ),
            bucket_bytes=bucket_bytes,
            total_bytes=bucket_bytes,
        )
