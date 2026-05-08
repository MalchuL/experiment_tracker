"""Mapping helpers between transport DTOs and storage-friendly shapes."""

from __future__ import annotations

from uuid import UUID

from object_storage.domain.buckets.dto import BucketListRowData

from .dto import (
    BucketListRowDTO,
    BlobCheckResponseDTO,
    DeleteBlobResponseDTO,
    SnapshotCreateResponseDTO,
    SnapshotFileEntryDTO,
    UploadBlobResponseDTO,
)


class ProjectArtifactsStorageMapper:
    """Mapper for project-artifacts DTOs and internal transport models."""

    def missing_hashes_to_response(self, missing: list[str]) -> BlobCheckResponseDTO:
        """Build a response DTO for CAS hash checks."""

        return BlobCheckResponseDTO(missing=missing)

    def snapshot_files_to_manifest(
        self, files: list[SnapshotFileEntryDTO]
    ) -> list[dict]:
        """Convert snapshot file DTOs into a JSON-serializable manifest."""

        return [entry.model_dump() for entry in files]

    def snapshot_id_to_response(self, snapshot_id: UUID) -> SnapshotCreateResponseDTO:
        """Wrap a snapshot UUID into the response DTO."""

        return SnapshotCreateResponseDTO(snapshot_id=str(snapshot_id))

    def upload_status_to_response(self, status: str) -> UploadBlobResponseDTO:
        """Wrap an upload status string into a response DTO."""

        return UploadBlobResponseDTO(status=status)

    def delete_blob_to_response(self, deleted: bool) -> DeleteBlobResponseDTO:
        """Wrap blob delete result into a response DTO."""

        return DeleteBlobResponseDTO(deleted=deleted)

    def bucket_row_data_to_response(self, row: BucketListRowData) -> BucketListRowDTO:
        """Convert internal bucket transport dataclass into API response model."""

        return BucketListRowDTO(
            id=row.id,
            project_id=row.project_id,
            experiment_id=row.experiment_id,
            name=row.name,
            size=row.size,
            storage_size=row.storage_size,
            object_count=row.object_count,
            created_at=row.created_at,
            registered=row.registered,
        )


def missing_hashes_to_response(missing: list[str]) -> BlobCheckResponseDTO:
    """Build a response DTO for CAS hash checks."""

    return ProjectArtifactsStorageMapper().missing_hashes_to_response(missing)


def snapshot_files_to_manifest(files: list[SnapshotFileEntryDTO]) -> list[dict]:
    """Convert snapshot file DTOs into a JSON-serializable manifest."""

    return ProjectArtifactsStorageMapper().snapshot_files_to_manifest(files)


def snapshot_id_to_response(snapshot_id: UUID) -> SnapshotCreateResponseDTO:
    """Wrap a snapshot UUID into the response DTO."""

    return ProjectArtifactsStorageMapper().snapshot_id_to_response(snapshot_id)


def upload_status_to_response(status: str) -> UploadBlobResponseDTO:
    """Wrap an upload status string into a response DTO."""

    return ProjectArtifactsStorageMapper().upload_status_to_response(status)


def delete_blob_to_response(deleted: bool) -> DeleteBlobResponseDTO:
    """Wrap blob delete result into a response DTO."""

    return ProjectArtifactsStorageMapper().delete_blob_to_response(deleted)
