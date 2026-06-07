from __future__ import annotations

from uuid import UUID

from typing import Any

from pydantic import BaseModel, Field

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from models import ExperimentDataType


class SnapshotFileEntryDTO(BaseModel):
    """One file entry in an experiment snapshot manifest.

    Args:
        path: POSIX-style relative path inside the snapshot archive.
        hash: SHA-256 content hash for the file, used to bind the manifest to
            content-addressed project artifacts.

    Result:
        A validated manifest item accepted by the backend snapshot upsert API.
    """

    model_config = model_config()

    path: str = Field(..., min_length=1, max_length=1024)
    hash: str = Field(..., min_length=64, max_length=64)
    size: int | None = Field(default=None, ge=0)


class ExperimentSnapshotUpsertDTO(BaseModel):
    """Request body for creating or replacing an experiment snapshot.

    Args:
        files: Complete manifest of snapshot files already uploaded or known in
            project content-addressed storage.

    Result:
        A validated request payload for the snapshot upsert route.
    """

    model_config = model_config()

    files: list[SnapshotFileEntryDTO]


class ExperimentDataDTO(BaseModel):
    """Generic API representation of an ``ExperimentData`` row.

    Args:
        id: Stable identifier of the data row.
        experiment_id: Experiment that owns the row.
        type: Logical data type stored in the row.
        data: JSON payload for the type-specific record.
        created_at: Row creation timestamp.
        updated_at: Row update timestamp.

    Result:
        Serializable DTO for generic experiment-data records.
    """

    model_config = model_config()

    id: UUID
    experiment_id: UUID
    type: ExperimentDataType
    data: dict
    created_at: ApiDateTime
    updated_at: ApiDateTime


class ExperimentHparamsUpsertDTO(BaseModel):
    """Complete replacement payload for an experiment's hyperparameters."""

    model_config = model_config()

    hparams: dict[str, Any]


class ExperimentHparamsDTO(BaseModel):
    """Current hyperparameter document and backing row metadata."""

    model_config = model_config()

    experiment_id: UUID
    type: ExperimentDataType = ExperimentDataType.HPARAMS
    hparams: dict[str, Any] | None = None
    data_id: UUID | None = None
    created_at: ApiDateTime | None = None
    updated_at: ApiDateTime | None = None


class ExperimentHparamsCompareRequestDTO(BaseModel):
    """Ordered experiment selection for project hparams comparison."""

    model_config = model_config()

    experiment_ids: list[UUID] = Field(..., min_length=1, max_length=20)


class ExperimentHparamsCompareItemDTO(BaseModel):
    model_config = model_config()

    experiment_id: UUID
    experiment_name: str
    hparams: dict[str, Any] | None = None


class ExperimentHparamsCompareResponseDTO(BaseModel):
    model_config = model_config()

    project_id: UUID
    experiments: list[ExperimentHparamsCompareItemDTO]


class ExperimentSnapshotDTO(BaseModel):
    """Public metadata for an experiment snapshot.

    Args:
        experiment_id: Experiment represented by this snapshot state.
        snapshot_id: Object-storage snapshot UUID, or ``None`` when no snapshot
            exists.
        data_id: Backing experiment-data row UUID, if present.
        created_at: Timestamp when the backing metadata row was created.
        updated_at: Timestamp when the snapshot metadata was last replaced.

    Result:
        Snapshot metadata returned by create, delete, and list APIs.
    """

    model_config = model_config()

    experiment_id: UUID
    snapshot_id: UUID | None = None
    data_id: UUID | None = None
    created_at: ApiDateTime | None = None
    updated_at: ApiDateTime | None = None


class ExperimentSnapshotsRequestDTO(BaseModel):
    """Request body for bulk snapshot metadata or file-preview queries.

    Args:
        experiment_ids: Non-empty list of experiments to resolve; capped to keep
            object-storage preview fan-out bounded.

    Result:
        Validated list request preserving the caller's experiment order.
    """

    model_config = model_config()

    experiment_ids: list[UUID] = Field(..., min_length=1, max_length=20)


class SnapshotFileManifestEntryDTO(BaseModel):
    """One file entry returned for compare tree rendering.

    Args:
        path: Relative snapshot path.
        hash: SHA-256 content hash for difference checks and lazy content fetches.
        size: Optional byte length when the storage backend can provide it cheaply.

    Result:
        Metadata-only file entry suitable for UI file trees.
    """

    model_config = model_config()

    path: str
    hash: str
    size: int | None = None


class ExperimentSnapshotFilesDTO(BaseModel):
    """Metadata-only file manifest payload for a single experiment snapshot.

    Args:
        experiment_id: Experiment whose snapshot was inspected.
        snapshot_id: Snapshot UUID, or ``None`` when no snapshot exists.
        files: Complete metadata-only manifest for the snapshot.

    Result:
        Snapshot file tree data without any file content.
    """

    model_config = model_config()

    experiment_id: UUID
    snapshot_id: UUID | None
    files: list[SnapshotFileManifestEntryDTO] = Field(default_factory=list)


class ExperimentSnapshotFilesResponseDTO(BaseModel):
    """Bulk response wrapper for snapshot file manifests.

    Args:
        items: Per-experiment snapshot preview results.

    Result:
        Top-level metadata-only API response for the snapshot files endpoint.
    """

    model_config = model_config()

    items: list[ExperimentSnapshotFilesDTO]


class ExperimentSnapshotFileContentRequestDTO(BaseModel):
    """Request body for loading one snapshot file by manifest identity."""

    model_config = model_config()

    path: str = Field(..., min_length=1, max_length=1024)
    hash: str = Field(..., min_length=64, max_length=64)


class ExperimentSnapshotFileContentDTO(BaseModel):
    """UTF-8 content payload for a single clicked snapshot file."""

    model_config = model_config()

    path: str
    hash: str
    content: str
    size: int
