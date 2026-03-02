from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class LogArtifactResponseDTO(BaseModel):
    status: str
    warnings: list[str] | None = None


class LogArtifactRequestDTO(BaseModel):
    name: str
    artifact_type: ArtifactType
    path: str
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None


class ObjectEntryDTO(BaseModel):
    timestamp: datetime
    step: int
    name: str
    object_type: ArtifactType
    path: str
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None


class ExperimentObjectsResultDTO(BaseModel):
    experiment_id: str
    objects: list[ObjectEntryDTO]


class ProjectObjectsResultDTO(BaseModel):
    data: list[ExperimentObjectsResultDTO]
