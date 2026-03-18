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
    artifact_type: ArtifactType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentArtifactsAtStepInfoResponse(BaseModel):
    experiment_id: str
    artifacts_info: list[ArtifactInfoAtStepEntryResponse]


class ArtifactsAtStepInfoResultResponse(BaseModel):
    data: list[ExperimentArtifactsAtStepInfoResponse]


class LogArtifactAtStepRequest(BaseModel):
    name: str
    artifact_type: ArtifactType
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

    deleted_count: int | None = None


class ExperimentArtifactResponse(BaseModel):
    id: UUID
    experiment_id: UUID
    name: str
    filepath: str
    filename: str
    mime_type: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
