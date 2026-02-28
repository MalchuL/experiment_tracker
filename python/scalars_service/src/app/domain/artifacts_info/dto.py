from datetime import datetime
from typing import Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class ArtifactInfoEntryDTO(BaseModel):
    timestamp: datetime
    step: int
    name: str
    artifact_type: ArtifactType
    path: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ExperimentArtifactsInfoResultDTO(BaseModel):
    experiment_id: UUID
    artifacts_info: List[ArtifactInfoEntryDTO]


class ArtifactsInfoResultDTO(BaseModel):
    data: List[ExperimentArtifactsInfoResultDTO]


class LogArtifactInfoRequestDTO(BaseModel):
    name: str
    artifact_type: ArtifactType
    path: str
    step: int
    metadata: Dict[str, str] | None = None
    tags: List[str] | None = None


class LogArtifactsInfoRequestDTO(BaseModel):
    artifacts: List[LogArtifactInfoRequestDTO]


class LogArtifactInfoResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None


class LogArtifactsInfoResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None
