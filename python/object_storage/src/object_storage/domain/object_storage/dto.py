"""Pydantic DTOs for the content-addressable storage API."""

from pydantic import BaseModel, Field


class BlobCheckResponseDTO(BaseModel):
    """Response DTO listing hashes that are missing from CAS storage."""

    missing: list[str] = Field(default_factory=list)


class SnapshotFileEntryDTO(BaseModel):
    """DTO describing one file in a snapshot manifest."""

    path: str
    hash: str
    size: int


class SnapshotCreateRequestDTO(BaseModel):
    """Request DTO for creating a snapshot from CAS-managed blobs."""

    experiment_name: str
    files: list[SnapshotFileEntryDTO]


class SnapshotCreateResponseDTO(BaseModel):
    """Response DTO containing the created snapshot identifier."""

    snapshot_id: str


class UploadBlobResponseDTO(BaseModel):
    """Response DTO describing the result of a blob upload."""

    status: str
