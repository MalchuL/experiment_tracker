from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from lib.datetime_types import ApiDateTime
from lib.pagination import PaginatedResponse


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


class SnapshotFileEntryDTO(BaseModel):
    path: str
    hash: str


class SnapshotCreateRequestDTO(BaseModel):
    project_id: UUID
    experiment_id: UUID
    files: list[SnapshotFileEntryDTO]


class ExperimentUntrackedUploadResponseDTO(BaseModel):
    """Object storage: POST .../upload-untracked response."""

    hash: str
    size: int


class ExperimentTrackedArtifactItemDTO(BaseModel):
    """One tracked experiment artifact row from object storage."""

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentTrackedArtifactListDTO(PaginatedResponse[ExperimentTrackedArtifactItemDTO]):
    pass


class ExperimentTrackedUploadResponseDTO(BaseModel):
    """Object storage: POST .../upload-tracked response."""

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentTrackedArtifactInfoDTO(BaseModel):
    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: ApiDateTime
    updated_at: ApiDateTime


class DeleteExperimentArtifactResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted: bool | None = None


class DeleteExperimentArtifactsResponseDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    deleted_count: int | None = None
