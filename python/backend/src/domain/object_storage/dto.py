from pydantic import BaseModel, Field


class BlobCheckResponseDTO(BaseModel):
    missing: list[str] = Field(default_factory=list)


class SnapshotFileEntryDTO(BaseModel):
    path: str
    hash: str
    size: int


class SnapshotCreateRequestDTO(BaseModel):
    experiment_name: str
    files: list[SnapshotFileEntryDTO]


class SnapshotCreateResponseDTO(BaseModel):
    snapshot_id: str
