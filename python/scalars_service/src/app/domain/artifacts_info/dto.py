from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.lib.datetime_types import ApiDateTime

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class ArtifactInfoEntryDTO(BaseModel):
    timestamp: ApiDateTime
    step: int
    name: str
    artifact_type: ArtifactType
    path: str
    metadata: Dict[str, str] = Field(
        default_factory=dict
    )  # Only strings supported in clickhouse
    tags: List[str] = Field(default_factory=list)


class ExperimentArtifactsInfoResultDTO(BaseModel):
    experiment_id: UUID
    artifacts_info: List[ArtifactInfoEntryDTO]


class ArtifactsInfoResultDTO(BaseModel):
    data: List[ExperimentArtifactsInfoResultDTO]
    has_next: bool = False
    size: int = 0
    total: int = 0


class ArtifactInfoSummaryEntryDTO(BaseModel):
    """Lightweight slider metadata for one artifact name/type within an experiment."""

    name: str
    artifact_type: ArtifactType
    steps: List[int]
    last_modified: ApiDateTime


class ExperimentArtifactsSummaryDTO(BaseModel):
    """Summary rows grouped by experiment, mirroring the full artifacts_info result shape."""

    experiment_id: UUID
    artifacts_info: List[ArtifactInfoSummaryEntryDTO]


class ArtifactsInfoSummaryResultDTO(BaseModel):
    """Paginated artifact summary response used by UI list/slider loading."""

    data: List[ExperimentArtifactsSummaryDTO]
    has_next: bool = False
    size: int = 0
    total: int = 0


class LogArtifactInfoRequestDTO(BaseModel):
    name: str
    artifact_type: ArtifactType
    path: str
    step: int
    metadata: Dict[str, str] | None = None  # Only strings supported in clickhouse
    tags: List[str] | None = None


class LogArtifactsInfoRequestDTO(BaseModel):
    artifacts: List[LogArtifactInfoRequestDTO]


class LogArtifactInfoResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None


class LogArtifactsInfoResponseDTO(BaseModel):
    status: str
    warnings: List[str] | None = None
