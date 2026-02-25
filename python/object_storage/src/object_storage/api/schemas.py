"""Compatibility layer for legacy schema imports."""

from object_storage.domain.object_storage.dto import (
    BlobCheckResponseDTO as BlobCheckResponse,
    DeleteBlobResponseDTO as DeleteBlobResponse,
    DeleteExperimentResponseDTO as DeleteExperimentResponse,
    SnapshotCreateRequestDTO as SnapshotCreateRequest,
    SnapshotCreateResponseDTO as SnapshotCreateResponse,
    SnapshotFileEntryDTO as SnapshotFileEntry,
    UploadBlobResponseDTO as UploadBlobResponse,
)
from object_storage.domain.artifacts_storage.dto import (
    DeleteArtifactResponseDTO as DeleteArtifactResponse,
    DeleteExperimentArtifactsResponseDTO as DeleteExperimentArtifactsResponse,
    ExperimentArtifactsSizeResponseDTO as ExperimentArtifactsSizeResponse,
    UploadArtifactResponseDTO as UploadArtifactResponse,
)

__all__ = [
    "BlobCheckResponse",
    "DeleteBlobResponse",
    "DeleteExperimentResponse",
    "SnapshotCreateRequest",
    "SnapshotCreateResponse",
    "SnapshotFileEntry",
    "UploadBlobResponse",
    "DeleteArtifactResponse",
    "DeleteExperimentArtifactsResponse",
    "ExperimentArtifactsSizeResponse",
    "UploadArtifactResponse",
]
