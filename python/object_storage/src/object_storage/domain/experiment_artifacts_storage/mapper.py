"""Mapping helpers for artifacts domain DTOs."""

from typing import Any

from object_storage.db.models import ExperimentBlob
from object_storage.domain.buckets.dto import UploadBlobResult

from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    TrackedArtifactInfoResponseDTO,
    TrackedUploadArtifactResponseDTO,
    UntrackedUploadArtifactResponseDTO,
)


class ArtifactsStorageMapper:

    def upload_artifact_to_untracked_response(
        self,
        upload_result: UploadBlobResult,
    ) -> UntrackedUploadArtifactResponseDTO:
        return UntrackedUploadArtifactResponseDTO(
            hash=upload_result.hash,
            size=upload_result.size,
        )

    def experiment_model_to_tracked_response(
        self, experiment_model: ExperimentBlob
    ) -> TrackedUploadArtifactResponseDTO:
        meta: dict[str, Any] = experiment_model.artifact_metadata or {}
        return TrackedUploadArtifactResponseDTO(
            id=experiment_model.id,
            hash=experiment_model.artifact_hash,
            file_path=experiment_model.file_path,
            mime_type=experiment_model.mime_type,
            size=experiment_model.size,
            metadata=meta,
        )

    def experiment_model_to_tracked_info_response(
        self, experiment_model: ExperimentBlob
    ) -> TrackedArtifactInfoResponseDTO:
        meta: dict[str, Any] = experiment_model.artifact_metadata or {}
        return TrackedArtifactInfoResponseDTO(
            id=experiment_model.id,
            hash=experiment_model.artifact_hash,
            file_path=experiment_model.file_path,
            mime_type=experiment_model.mime_type,
            size=experiment_model.size,
            metadata=meta,
            created_at=experiment_model.created_at,
            updated_at=experiment_model.updated_at,
        )

    def delete_artifact_to_response(self, deleted: bool) -> DeleteArtifactResponseDTO:
        return DeleteArtifactResponseDTO(deleted=deleted)

    def delete_experiment_to_response(
        self, deleted_count: int
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=deleted_count)
