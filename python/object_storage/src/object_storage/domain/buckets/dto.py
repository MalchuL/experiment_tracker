from __future__ import annotations

from dataclasses import dataclass
from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class BucketObjectStats:
    """Totals from one bucket listing pass (object count and summed byte sizes)."""

    object_count: int
    storage_bytes: int


class UploadBlobResult(BaseModel):
    """Result of a blob upload."""

    size: int
    hash: str


@dataclass(frozen=True, slots=True)
class BucketListRowData:
    """Internal bucket row between repository, storage client, and HTTP DTO mapping.

    Attributes:
        size: Registry byte total (``Bucket.size`` in Postgres), maintained on upload/delete.
        storage_size: Sum of blob sizes from ``list_blob_entries`` when the list operation
            used ``reconcile=True``; otherwise ``None``. Read-only for the caller—does not
            update the registry. Persisted fixes use ``reconcile_bucket_by_id``.
        object_count: Length of the blob entry listing for this row.
    """

    id: str | None
    project_id: str | None
    experiment_id: str | None
    name: str
    size: int
    storage_size: int | None
    object_count: int
    created_at: str | None
    registered: bool


@dataclass(frozen=True, slots=True)
class BucketListResultData:
    """Internal paginated buckets result transport (rows + total count)."""

    rows: list[BucketListRowData]
    total: int


@dataclass(frozen=True, slots=True)
class BucketReconcileResultData:
    """Result of ``reconcile_bucket_by_id``: recompute registry ``size`` from storage.

    Attributes:
        found: Whether the bucket id existed in the registry.
        size: Byte total written to the registry (sum of storage object sizes).
        object_count: Number of objects listed in storage for that sum.
    """

    found: bool
    size: int
    object_count: int
