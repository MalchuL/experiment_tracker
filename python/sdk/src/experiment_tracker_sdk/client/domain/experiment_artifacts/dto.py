from __future__ import annotations

from datetime import datetime
from uuid import UUID

from experiment_tracker_shared import ArtifactType
from pydantic import BaseModel, ConfigDict, Field

from ...pagination import PaginatedResponse


class ArtifactInfoAtStepEntryResponse(BaseModel):
    timestamp: datetime
    step: int
    name: str
    artifactType: ArtifactType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentArtifactsAtStepInfoResponse(BaseModel):
    experimentId: str
    artifactsInfo: list[ArtifactInfoAtStepEntryResponse]


class ArtifactsAtStepInfoResultResponse(
    PaginatedResponse[ExperimentArtifactsAtStepInfoResponse]
):
    pass


class ArtifactInfoAtStepSummaryEntryResponse(BaseModel):
    """SDK response row for lightweight at-step artifact slider metadata."""

    name: str
    artifactType: ArtifactType
    steps: list[int]
    lastModified: datetime


class ExperimentArtifactsAtStepSummaryResponse(BaseModel):
    """SDK summary rows grouped by experiment."""

    experimentId: str
    artifactsInfo: list[ArtifactInfoAtStepSummaryEntryResponse]


class ArtifactsAtStepSummaryResultResponse(
    PaginatedResponse[ExperimentArtifactsAtStepSummaryResponse]
):
    """Paginated SDK response for at-step artifact summaries."""

    pass


class LogArtifactAtStepRequest(BaseModel):
    name: str
    artifactType: ArtifactType
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None


class LogArtifactAtStepResponse(BaseModel):
    status: str
    warnings: list[str] | None = None


class DeleteExperimentArtifactAtStepResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteExperimentArtifactsAtStepResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deletedCount: int | None = None


class ExperimentArtifactResponse(BaseModel):
    id: UUID
    experimentId: UUID
    name: str
    filepath: str
    filename: str
    mimeType: str
    storagePath: str
    createdAt: datetime
    updatedAt: datetime


class ExperimentArtifactListResponse(PaginatedResponse[ExperimentArtifactResponse]):
    pass
