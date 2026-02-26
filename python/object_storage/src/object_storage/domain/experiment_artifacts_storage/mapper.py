"""Mapping helpers for artifacts domain DTOs."""

from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ExperimentArtifactsSizeResponseDTO,
    UploadArtifactResponseDTO,
)


def upload_to_response(
    path: str, size: int, status: str = "ok"
) -> UploadArtifactResponseDTO:
    """Build upload response DTO."""

    return UploadArtifactResponseDTO(status=status, path=path, size=size)


def delete_artifact_to_response(deleted: bool) -> DeleteArtifactResponseDTO:
    """Build artifact delete response DTO."""

    return DeleteArtifactResponseDTO(deleted=deleted)


def delete_experiment_to_response(
    deleted_count: int,
) -> DeleteExperimentArtifactsResponseDTO:
    """Build experiment artifact delete response DTO."""

    return DeleteExperimentArtifactsResponseDTO(deleted_count=deleted_count)


def size_to_response(total_size_bytes: int) -> ExperimentArtifactsSizeResponseDTO:
    """Build experiment artifacts size response DTO."""

    return ExperimentArtifactsSizeResponseDTO(total_size_bytes=total_size_bytes)
