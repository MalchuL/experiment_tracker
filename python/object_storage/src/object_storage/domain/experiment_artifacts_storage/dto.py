"""Pydantic DTOs for experiment-scoped artifacts storage."""

from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID
from pydantic import BaseModel


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


class ExperimentArtifactsSizeResponseDTO(BaseModel):
    """Response DTO returning total artifacts size for one experiment."""

    total_size_bytes: int


class ListArtifactsResponseDTO(BaseModel):
    """Response DTO listing all artifacts for an experiment."""

    artifacts: list[str]
