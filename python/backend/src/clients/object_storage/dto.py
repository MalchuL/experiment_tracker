from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CheckProjectArtifactsResponseDTO(BaseModel):
    missing: list[str]


class UploadProjectArtifactResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None


class DeleteProjectArtifactResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteProjectResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class SnapshotCreateResponseDTO(BaseModel):
    snapshot_id: str


class UploadExperimentArtifactResponseDTO(BaseModel):
    path: str
    size: int


class DeleteExperimentArtifactResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteExperimentArtifactsResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted_count: int | None = None

