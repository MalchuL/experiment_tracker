from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactType = Literal["image", "video", "audio", "text", "point_cloud_3d"]


class ArtifactInfoEntryResponse(BaseModel):
    timestamp: datetime
    step: int
    name: str
    artifact_type: ArtifactType
    path: str
    metadata: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ExperimentArtifactsInfoResponse(BaseModel):
    experiment_id: str
    artifacts_info: list[ArtifactInfoEntryResponse]


class ArtifactsInfoResultResponse(BaseModel):
    data: list[ExperimentArtifactsInfoResponse]


class LogArtifactRequest(BaseModel):
    name: str
    artifact_type: ArtifactType
    step: int
    metadata: dict[str, str] | None = None
    tags: list[str] | None = None


class LogArtifactResponse(BaseModel):
    status: str
    warnings: list[str] | None = None


class DeleteExperimentArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteExperimentArtifactsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted_count: int | None = None
