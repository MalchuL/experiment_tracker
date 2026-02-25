"""Pydantic DTOs for experiment-scoped artifacts storage."""

from pydantic import BaseModel


class UploadArtifactResponseDTO(BaseModel):
    """Response DTO for artifact upload."""

    status: str
    path: str
    size: int


class DeleteArtifactResponseDTO(BaseModel):
    """Response DTO describing whether an artifact was deleted."""

    deleted: bool


class DeleteExperimentArtifactsResponseDTO(BaseModel):
    """Response DTO for deleting all artifacts of an experiment."""

    deleted_count: int


class ExperimentArtifactsSizeResponseDTO(BaseModel):
    """Response DTO returning total artifacts size for one experiment."""

    total_size_bytes: int
