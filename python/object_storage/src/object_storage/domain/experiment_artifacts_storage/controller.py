"""FastAPI controller for experiment-scoped artifacts storage."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.responses import StreamingResponse

from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    UploadArtifactResponseDTO,
)
from .service import ArtifactsStorageService
from object_storage.storage import StorageBackend, get_storage

router = APIRouter(prefix="/artifacts")


def _build_service(storage: StorageBackend) -> ArtifactsStorageService:
    """Create artifacts service instance for a request."""

    return ArtifactsStorageService(storage)


@router.post("/upload", response_model=UploadArtifactResponseDTO)
async def upload_artifact(
    experiment_id: UUID = Query(...),
    file: UploadFile = File(...),
    storage: StorageBackend = Depends(get_storage),
):
    """Upload one artifact file for an experiment."""

    service = _build_service(storage)
    return await service.upload_artifact(experiment_id, file)


@router.get("/{experiment_id}")
async def download_artifact(
    experiment_id: UUID,
    path: str = Query(..., min_length=1),
    storage: StorageBackend = Depends(get_storage),
):
    """Stream one artifact for an experiment and path."""

    service = _build_service(storage)
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
    storage: StorageBackend = Depends(get_storage),
):
    """Delete one artifact for an experiment."""

    service = _build_service(storage)
    return await service.delete_artifact(experiment_id, path)


@router.delete(
    "/experiments/{experiment_id}", response_model=DeleteExperimentArtifactsResponseDTO
)
async def delete_experiment_artifacts(
    experiment_id: UUID,
    storage: StorageBackend = Depends(get_storage),
):
    """Delete all artifacts for one experiment."""

    service = _build_service(storage)
    return await service.delete_experiment(experiment_id)
