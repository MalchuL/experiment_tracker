from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SnapshotFileEntry(BaseModel):
    """Client-side snapshot manifest entry.

    Args:
        path: POSIX-style relative path inside the snapshot archive.
        hash: SHA-256 content hash for the file.

    Result:
        Validated manifest item sent to the backend experiment-data API.
    """

    path: str
    hash: str = Field(..., min_length=64, max_length=64)
    size: int | None = Field(default=None, ge=0)


class ExperimentSnapshotUpsertRequest(BaseModel):
    """Payload for upserting an experiment snapshot manifest.

    Args:
        files: Complete list of manifest entries to associate with the
            experiment snapshot.

    Result:
        Request body serialized by the SDK HTTP client.
    """

    files: list[SnapshotFileEntry]


class ExperimentSnapshotResponse(BaseModel):
    """Response returned by the backend after snapshot metadata upsert.

    Args:
        experiment_id: Experiment UUID returned by the backend.
        snapshot_id: Snapshot UUID assigned by object storage, if present.
        data_id: Backend metadata row UUID, if present.

    Result:
        Parsed snapshot metadata with additional backend fields allowed.
    """

    model_config = ConfigDict(extra="allow")

    experiment_id: UUID | str = Field(alias="experimentId")
    snapshot_id: UUID | str | None = Field(default=None, alias="snapshotId")
    data_id: UUID | str | None = Field(default=None, alias="dataId")
