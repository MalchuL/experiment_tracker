"""FastAPI controller for experiment-scoped artifacts storage."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.responses import StreamingResponse

from object_storage.api.service_dependencies import get_experiment_artifacts_service
from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    UploadArtifactResponseDTO,
)
from .service import ArtifactsStorageService

router = APIRouter(prefix="/experiment-artifacts")


@router.post("/{experiment_id}/upload", response_model=UploadArtifactResponseDTO)
async def upload_artifact(
    experiment_id: UUID,
    file: UploadFile = File(...),
    path: str | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Upload one artifact file for an experiment."""

    return await service.upload_artifact(experiment_id, file, path=path)


@router.get("/{experiment_id}/download")
async def download_artifact(
    experiment_id: UUID,
    path: str = Query(..., min_length=1),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Stream one artifact for an experiment and path."""

    artifact_stream = await service.get_artifact_stream(experiment_id, path)

    async def _iter_stream():
        try:
            for chunk in artifact_stream.stream(32 * 1024):
                yield chunk
        finally:
            artifact_stream.close()
            artifact_stream.release_conn()

    return StreamingResponse(_iter_stream(), media_type="application/octet-stream")


@router.delete("/{experiment_id}", response_model=DeleteArtifactResponseDTO)
async def delete_artifact(
    experiment_id: UUID,
    path: str = Query(..., min_length=1),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Delete one artifact for an experiment."""

    return await service.delete_artifact(experiment_id, path)


@router.delete(
    "/experiments/{experiment_id}", response_model=DeleteExperimentArtifactsResponseDTO
)
async def delete_experiment_artifacts(
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Delete all artifacts for one experiment."""

    return await service.delete_experiment(experiment_id)
