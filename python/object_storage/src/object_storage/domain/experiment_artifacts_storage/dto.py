"""Pydantic DTOs for experiment-scoped artifacts storage."""

from dataclasses import dataclass
from typing import Any, BinaryIO
from uuid import UUID

from pydantic import BaseModel, Field

from object_storage.lib.datetime_types import ApiDateTime
from object_storage.lib.dto_config import model_config


class UntrackedUploadArtifactResponseDTO(BaseModel):
    """Response DTO for uploading an artifact."""

    hash: str
    size: int


class TrackedUploadArtifactResponseDTO(BaseModel):
    """Response DTO for uploading an artifact."""

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrackedArtifactsListResponseDTO(BaseModel):
    """Paginated tracked artifact list for one experiment."""

    data: list[TrackedUploadArtifactResponseDTO]
    has_next: bool
    size: int
    total: int = 0


class TrackedArtifactInfoResponseDTO(BaseModel):
    """Tracked artifact metadata stored in DB."""

    id: UUID
    hash: str
    file_path: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: ApiDateTime
    updated_at: ApiDateTime


@dataclass
class ArtifactStreamResponseDTO:
    """Response DTO for streaming an artifact."""

    stream: BinaryIO
    size: int | None = None
    mime_type: str = "application/octet-stream"
    filename: str | None = None
    file_path: str | None = None


class DeleteArtifactResponseDTO(BaseModel):
    """Response DTO describing whether an artifact was deleted."""

    deleted: bool


class DeleteExperimentArtifactsResponseDTO(BaseModel):
    """Response DTO for deleting all artifacts of an experiment."""

    deleted_count: int


class EnsureExperimentBucketResponseDTO(BaseModel):
    """Response DTO after provisioning the experiment-scoped storage bucket."""

    bucket_name: str


class ExperimentArtifactsSizeResponseDTO(BaseModel):
    """Response DTO returning total artifacts size for one experiment."""

    total_size_bytes: int


class ExperimentArtifactsUsageItemDTO(BaseModel):
    """Usage counters for one experiment artifact category."""

    model_config = model_config()

    count: int
    bytes: int


class ExperimentArtifactsUsageResponseDTO(BaseModel):
    """Usage payload returned by experiment artifacts usage endpoints."""

    model_config = model_config()

    project_id: str
    experiment_id: str
    experiment_artifacts: ExperimentArtifactsUsageItemDTO
    at_step_artifacts: ExperimentArtifactsUsageItemDTO
    bucket_bytes: int
    total_bytes: int
