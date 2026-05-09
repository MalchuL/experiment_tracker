from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


class CheckProjectArtifactsResponseDTO(BaseModel):
    model_config = model_config()

    missing: list[str]


class UploadProjectArtifactResponseDTO(BaseModel):
    model_config = model_config()

    status: str | None = None


class DeleteProjectArtifactResponseDTO(BaseModel):
    model_config = model_config()

    deleted: bool | None = None


class DeleteProjectResponseDTO(BaseModel):
    model_config = model_config()

    deleted: bool | None = None


class SnapshotCreateResponseDTO(BaseModel):
    model_config = model_config()

    snapshot_id: str


class SnapshotFileEntryDTO(BaseModel):
    model_config = model_config()

    path: str
    hash: str


class SnapshotCreateRequestDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    experiment_id: UUID
    files: list[SnapshotFileEntryDTO]


class ExperimentUntrackedUploadResponseDTO(BaseModel):
    """Object storage: POST .../upload-untracked response."""

    model_config = model_config()

    hash: str
    size: int


class ExperimentTrackedArtifactItemDTO(BaseModel):
    """One tracked experiment artifact row from object storage."""

    model_config = model_config()

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentTrackedArtifactListDTO(PaginatedResponse[ExperimentTrackedArtifactItemDTO]):
    model_config = model_config()


class ExperimentTrackedUploadResponseDTO(BaseModel):
    """Object storage: POST .../upload-tracked response."""

    model_config = model_config()

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentTrackedArtifactInfoDTO(BaseModel):
    model_config = model_config()

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: ApiDateTime
    updated_at: ApiDateTime


class DeleteExperimentArtifactResponseDTO(BaseModel):
    model_config = model_config()

    deleted: bool | None = None


class DeleteExperimentArtifactsResponseDTO(BaseModel):
    model_config = model_config()

    deleted_count: int | None = None


class DeleteProjectSnapshotResponseDTO(BaseModel):
    """Object storage: DELETE .../snapshots/{snapshot_id} response."""

    model_config = model_config()

    deleted: bool
    deleted_blobs: list[str] = Field(default_factory=list)


class ProjectArtifactsUsageItemDTO(BaseModel):
    """Usage block with count/bytes."""

    model_config = model_config()

    count: int = 0
    bytes: int = 0


class ProjectSnapshotsUsageDTO(BaseModel):
    """Snapshot usage payload for project-scoped CAS data."""

    model_config = model_config()

    count: int = 0
    referenced_blob_count: int = 0
    bytes: int = 0


class StorageBucketRowDTO(BaseModel):
    """One row from object-storage bucket listing or usage payloads.

    **Two byte fields:** ``size`` is the registry counter (cheap, updated on normal
    upload/delete). ``storage_size`` is the sum of sizes from an actual object-store
    listing for *this response only* when the list call used ``reconcile=true``; it is
    ``null`` otherwise and **does not** persist any fix. To rewrite the registry counter
    from storage, call ``POST .../admin/storage/buckets/{bucket_id}/reconcile`` on
    object_storage.
    """

    model_config = model_config()

    id: str | None = None
    project_id: str | None = None
    experiment_id: str | None = None
    name: str
    size: int = Field(
        default=0,
        description=(
            "Byte total stored in the object-storage registry for this bucket "
            "(incremental book-keeping). May drift if blobs changed outside the app."
        ),
    )
    storage_size: int | None = Field(
        default=None,
        description=(
            "Sum of object sizes reported by S3/MinIO for this response. Present only "
            "when the list request used reconcile=true (extra list pass); null if skipped. "
            "Read-only for the request—does not update the registry."
        ),
    )
    object_count: int = Field(
        default=0,
        description="Number of objects seen in the bucket listing for this row.",
    )
    created_at: str | None = None
    registered: bool = False


class ExperimentBucketsUsageDTO(BaseModel):
    """Aggregated usage over experiment-scoped buckets."""

    model_config = model_config()

    count: int = 0
    bytes: int = 0


class ProjectUsageResponseDTO(BaseModel):
    """Object storage: GET .../project-artifacts/{project_id}/usage response."""

    model_config = model_config()

    project_id: str
    project_artifacts: ProjectArtifactsUsageItemDTO
    snapshots: ProjectSnapshotsUsageDTO
    experiment_buckets: ExperimentBucketsUsageDTO
    project_bucket: StorageBucketRowDTO | None = None
    total_bytes: int = 0


class ExperimentArtifactsUsageResponseDTO(BaseModel):
    """Object storage: GET .../experiment-artifacts/.../usage response."""

    model_config = model_config()

    project_id: str
    experiment_id: str
    experiment_artifacts: ProjectArtifactsUsageItemDTO
    at_step_artifacts: ProjectArtifactsUsageItemDTO
    bucket_bytes: int = 0
    total_bytes: int = 0


class StorageBucketListResponseDTO(BaseModel):
    """Object storage: GET .../storage/buckets response.

    Pass ``reconcile=true`` on the HTTP query to populate each row's ``storage_size``
    (live sum from the blob store). That flag is **read-only** for the registry
    ``size`` field; use per-bucket POST reconcile to persist a corrected total.
    """

    model_config = model_config()

    buckets: list[StorageBucketRowDTO] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


class StorageBucketDeleteResponseDTO(BaseModel):
    """Object storage bucket delete response."""

    model_config = model_config()

    deleted: bool = False


class StorageBucketClearResponseDTO(BaseModel):
    """Object storage bucket clear response."""

    model_config = model_config()

    cleared: bool = False


class StorageBucketReconcileResponseDTO(BaseModel):
    """Object storage: POST .../buckets/{bucket_id}/reconcile response.

    Recomputes byte total from the object store and **persists** it as the registry
    ``size`` for that bucket. This differs from GET list's ``reconcile`` query flag,
    which only fills ``storage_size`` on the response without writing to the DB.
    """

    model_config = model_config()

    found: bool = Field(
        default=False,
        description="Whether a registry row existed for the given bucket id.",
    )
    size: int = Field(
        default=0,
        description="Registry byte total after reconciliation (written to Postgres).",
    )
    object_count: int = Field(
        default=0,
        description="Object count from the storage listing used for reconciliation.",
    )
