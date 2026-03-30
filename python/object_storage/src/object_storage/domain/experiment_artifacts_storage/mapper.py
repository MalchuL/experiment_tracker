"""Mapping helpers for artifacts domain DTOs."""

from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    UntrackedUploadArtifactResponseDTO,
    TrackedUploadArtifactResponseDTO,
)
from object_storage.domain.buckets.dto import UploadBlobResult
from object_storage.db.models import ExperimentBlob
from uuid import UUID


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
        return TrackedUploadArtifactResponseDTO(
            id=experiment_model.id,
            hash=experiment_model.artifact_hash,
            file_path=experiment_model.file_path,
            mime_type=experiment_model.mime_type,
            size=experiment_model.size,
        )

    def delete_artifact_to_response(self, deleted: bool) -> DeleteArtifactResponseDTO:
        return DeleteArtifactResponseDTO(deleted=deleted)

    def delete_experiment_to_response(
        self, deleted_count: int
    ) -> DeleteExperimentArtifactsResponseDTO:
        return DeleteExperimentArtifactsResponseDTO(deleted_count=deleted_count)

    def create_experiment_model(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_hash: str,
        filename: str,
        mime_type: str,
    ) -> ExperimentBlob:
        return ExperimentBlob(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_hash=artifact_hash,
            filename=filename,
            mime_type=mime_type,
        )
