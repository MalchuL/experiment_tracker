"""Pydantic DTOs for the content-addressable storage API."""

from uuid import UUID

from pydantic import BaseModel, Field

from object_storage.lib.dto_config import model_config

# Matches ``ExperimentBlob.file_path`` / tracked-artifact relative path storage.
_ARTIFACT_FILE_PATH_MAX_LEN = 1024


class BlobCheckResponseDTO(BaseModel):
    """Response DTO listing hashes that are missing from CAS storage."""

    missing: list[str] = Field(default_factory=list)


class SnapshotFileEntryDTO(BaseModel):
    """DTO describing one file in a snapshot manifest."""

    path: str = Field(..., min_length=1, max_length=_ARTIFACT_FILE_PATH_MAX_LEN)
    hash: str = Field(..., min_length=64, max_length=64)
    size: int | None = Field(default=None, ge=0)


class SnapshotCreateRequestDTO(BaseModel):
    """Request DTO for creating a snapshot from CAS-managed blobs."""

    project_id: UUID
    experiment_id: UUID
    files: list[SnapshotFileEntryDTO]


class SnapshotCreateResponseDTO(BaseModel):
    """Response DTO containing the created snapshot identifier."""

    snapshot_id: str


class SnapshotManifestResponseDTO(BaseModel):
    """Response DTO containing a snapshot's stored file manifest."""

    snapshot_id: UUID
    files: list[SnapshotFileEntryDTO] = Field(default_factory=list)


class UploadBlobResponseDTO(BaseModel):
    """Response DTO describing the result of a blob upload."""

    status: str


class DeleteBlobResponseDTO(BaseModel):
    """Response DTO describing whether a blob was deleted."""

    deleted: bool


class DeleteProjectResponseDTO(BaseModel):
    """Response DTO describing whether a project was deleted."""

    deleted: bool


class BucketListRowDTO(BaseModel):
    """API bucket row used by admin listing and usage responses.

    **``size``** is the registry byte counter (maintained incrementally). **``storage_size``**
    is the sum of blob sizes from an object-store listing **for this response only** when
    ``GET .../admin/storage/buckets`` was called with ``reconcile=true``; otherwise it is
    ``null``. That query parameter does **not** update ``size`` in the database. To
    persist a corrected total from storage, call ``POST .../admin/storage/buckets/{bucket_id}/reconcile``.
    """

    model_config = model_config()

    id: str | None
    project_id: str | None
    experiment_id: str | None
    name: str
    size: int = Field(
        description=(
            "Byte total in the object-storage registry for this bucket (incremental "
            "book-keeping); may drift from S3/MinIO if objects changed out-of-band."
        ),
    )
    storage_size: int | None = Field(
        description=(
            "Live sum of object sizes from storage listing when reconcile=true on GET "
            "admin list; null when omitted (default). Read-only for that request."
        ),
    )
    object_count: int = Field(
        description="Number of objects returned by the storage listing for this row.",
    )
    created_at: str | None
    registered: bool


class ProjectArtifactsUsageItemDTO(BaseModel):
    """Usage totals for a single storage category."""

    model_config = model_config()

    count: int
    bytes: int


class ProjectSnapshotsUsageDTO(BaseModel):
    """Snapshot usage totals for one project."""

    model_config = model_config()

    count: int
    referenced_blob_count: int
    bytes: int


class ExperimentBucketsUsageDTO(BaseModel):
    """Aggregate usage for experiment-scoped buckets of one project."""

    model_config = model_config()

    count: int
    bytes: int


class ProjectUsageResponseDTO(BaseModel):
    """Complete usage payload returned by project usage endpoints."""

    model_config = model_config()

    project_id: str
    project_artifacts: ProjectArtifactsUsageItemDTO
    snapshots: ProjectSnapshotsUsageDTO
    experiment_buckets: ExperimentBucketsUsageDTO
    project_bucket: BucketListRowDTO | None
    total_bytes: int


class BucketListResponseDTO(BaseModel):
    """Paginated admin response for listing object-storage buckets.

    Optional query ``reconcile=true`` fills ``storage_size`` on each row (expensive).
    It does not persist registry fixes; use POST ``.../buckets/{bucket_id}/reconcile`` for that.
    """

    model_config = model_config()

    buckets: list[BucketListRowDTO]
    total: int
    limit: int
    offset: int


class DeleteStorageBucketResponseDTO(BaseModel):
    """Boolean response for bucket delete operations."""

    model_config = model_config()

    deleted: bool


class ClearStorageBucketResponseDTO(BaseModel):
    """Boolean response for bucket clear operations."""

    model_config = model_config()

    cleared: bool


class ReconcileStorageBucketResponseDTO(BaseModel):
    """Response after ``POST .../admin/storage/buckets/{bucket_id}/reconcile``.

    Re-sums object bytes from S3/MinIO and **writes** that value to the registry ``size``.
    Unlike GET list's ``reconcile`` query flag, this endpoint persists the correction.
    """

    model_config = model_config()

    found: bool = Field(description="True if a registry bucket row existed for bucket_id.")
    size: int = Field(
        description="Registry byte total after persist (matches storage sum at reconcile time).",
    )
    object_count: int = Field(
        description="Number of objects counted in storage during reconciliation.",
    )


class DeleteProjectSnapshotResponseDTO(BaseModel):
    """Response payload for deleting one project snapshot."""

    model_config = model_config()

    deleted: bool
    deleted_blobs: list[str]
