"""Mapping helpers between transport DTOs and storage-friendly shapes."""

from __future__ import annotations

from uuid import UUID

from object_storage.domain.object_storage.dto import (
    BlobCheckResponseDTO,
    SnapshotCreateResponseDTO,
    SnapshotFileEntryDTO,
    UploadBlobResponseDTO,
)


def missing_hashes_to_response(missing: list[str]) -> BlobCheckResponseDTO:
    """Build a response DTO for CAS hash checks."""

    return BlobCheckResponseDTO(missing=missing)


def snapshot_files_to_manifest(files: list[SnapshotFileEntryDTO]) -> list[dict]:
    """Convert snapshot file DTOs into a JSON-serializable manifest."""

    return [entry.model_dump() for entry in files]


def snapshot_id_to_response(snapshot_id: UUID) -> SnapshotCreateResponseDTO:
    """Wrap a snapshot UUID into the response DTO."""

    return SnapshotCreateResponseDTO(snapshot_id=str(snapshot_id))


def upload_status_to_response(status: str) -> UploadBlobResponseDTO:
    """Wrap an upload status string into a response DTO."""

    return UploadBlobResponseDTO(status=status)
