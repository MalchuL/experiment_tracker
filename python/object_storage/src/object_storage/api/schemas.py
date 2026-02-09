"""Compatibility layer for legacy schema imports."""

from object_storage.domain.object_storage.dto import (
    BlobCheckResponseDTO as BlobCheckResponse,
    SnapshotCreateRequestDTO as SnapshotCreateRequest,
    SnapshotCreateResponseDTO as SnapshotCreateResponse,
    SnapshotFileEntryDTO as SnapshotFileEntry,
    UploadBlobResponseDTO as UploadBlobResponse,
)

__all__ = [
    "BlobCheckResponse",
    "SnapshotCreateRequest",
    "SnapshotCreateResponse",
    "SnapshotFileEntry",
    "UploadBlobResponse",
]
