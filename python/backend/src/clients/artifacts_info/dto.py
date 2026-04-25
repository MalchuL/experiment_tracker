from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from lib.pagination import PaginatedResponse

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


class ArtifactInfoEntryDTO(BaseModel):
    timestamp: datetime
    step: int
    name: str
    artifact_type: ArtifactType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentArtifactsInfoDTO(BaseModel):
    """
    DTO for a single experiment's artifacts info.
    Args:
        experiment_id: The ID of the experiment.
        artifacts_info: The list of artifacts info.
    Notes:
        - The artifacts info is grouped by experiment but not by name.
    """

    experiment_id: UUID
    artifacts_info: list[ArtifactInfoEntryDTO]


class ArtifactsInfoResultDTO(PaginatedResponse[ExperimentArtifactsInfoDTO]):
    pass
