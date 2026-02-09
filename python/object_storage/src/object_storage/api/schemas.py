from pydantic import BaseModel, Field


class BlobCheckResponse(BaseModel):
    missing: list[str] = Field(default_factory=list)


class SnapshotFileEntry(BaseModel):
    path: str
    hash: str
    size: int


class SnapshotCreateRequest(BaseModel):
    experiment_name: str
    files: list[SnapshotFileEntry]


class SnapshotCreateResponse(BaseModel):
    snapshot_id: str
