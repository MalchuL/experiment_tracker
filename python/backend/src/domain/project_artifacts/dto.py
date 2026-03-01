from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class LogArtifactRequestDTO(BaseModel):
    name: str
    artifact_type: ArtifactType
    path: str
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None


class LogArtifactResponseDTO(BaseModel):
    status: str
    warnings: list[str] | None = None


class SnapshotFileEntryDTO(BaseModel):
    path: str
    hash: str


class SnapshotCreateRequestDTO(BaseModel):
    project_id: UUID
    experiment_id: UUID
    files: list[SnapshotFileEntryDTO]


class SnapshotCreateResponseDTO(BaseModel):
    snapshot_id: str


class ArtifactEntryDTO(BaseModel):
    timestamp: datetime
    step: int
    name: str
    artifact_type: ArtifactType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentArtifactsResultDTO(BaseModel):
    experiment_id: str
    artifacts_info: list[ArtifactEntryDTO]


class ArtifactsResultDTO(BaseModel):
    data: list[ExperimentArtifactsResultDTO]
