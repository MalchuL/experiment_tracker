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
        """Check if the hash is valid."""
        if not re.fullmatch(r"^[0-9a-fA-F]{4,64}$", hash):
            raise HashNotValidError(
                f"Hash {hash} is not valid, must be 4-64 hex characters"
            )

    async def upload_artifact_and_forget(
        self,
        project_id: UUID,
        experiment_id: UUID,
        upload: UploadFile,
        hash: str | None = None,
    ) -> UntrackedUploadArtifactResponseDTO:
        """
        Upload one artifact under an experiment-specific prefix.
        Used to store artifact that are not part of the experiment manifest.
        Currently used to store not final data in training like image, video, etc.

        Args:
            project_id: The ID of the project.
            experiment_id: The ID of the experiment.
            upload: The upload file.
            hash: The hash of the artifact that used to store in storage.

        Returns:
            The response from the object storage.
            The response contains the hash and size of the uploaded artifact.
        """
        artifact_hash = hash or uuid4().hex
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
        hash: str | None = None,
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
            hash: The hash of the artifact that used to store in storage.
            file_path: Relative path for the tracked blob (stored on the row).
            metadata: Optional JSON object stored as-is on the blob row (default ``{}``).

        Returns:
            The response from the object storage.
            The response contains the hash and size of the uploaded artifact.
        """
        artifact_hash = hash or uuid4().hex
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
        self, project_id: UUID, experiment_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[TrackedUploadArtifactResponseDTO]:
        """List all artifacts for an experiment."""

        blobs = await self._artifacts_repository.list_experiment_blobs(
            project_id, experiment_id, limit, offset
        )
        return [
            self._mapper.experiment_model_to_tracked_response(blob) for blob in blobs
        ]

    async def get_artifact_stream(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        tracked: bool = False,
    ) -> ArtifactStreamResponseDTO:
        """Get a streaming handle for one artifact."""
        if tracked:
            blob = await self._artifacts_repository.get_experiment_blob(
                project_id, experiment_id, artifact_hash
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
        else:
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

    async def delete_artifact(
        self, project_id: UUID, experiment_id: UUID, artifact_hash: str
    ) -> DeleteArtifactResponseDTO:
        """Delete one artifact for an experiment."""
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
        return self._mapper.delete_experiment_to_response(deleted_count=0)
