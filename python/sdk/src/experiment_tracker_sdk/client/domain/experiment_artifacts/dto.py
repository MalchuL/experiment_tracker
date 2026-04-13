from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


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


class ArtifactsAtStepInfoResultResponse(BaseModel):
    data: list[ExperimentArtifactsAtStepInfoResponse]


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
