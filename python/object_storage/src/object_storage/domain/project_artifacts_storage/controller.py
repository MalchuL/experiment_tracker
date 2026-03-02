"""FastAPI controller for the CAS object storage domain."""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from object_storage.api.service_dependencies import get_project_artifacts_service
from .dto import (
    BlobCheckResponseDTO,
    DeleteBlobResponseDTO,
    DeleteProjectResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadBlobResponseDTO,
)
from .service import ObjectStorageService

router = APIRouter(prefix="/project-artifacts")


@router.post("/{project_id}/check", response_model=BlobCheckResponseDTO)
async def check_project_artifacts(
    project_id: UUID,
    hashes: list[str] = Body(..., embed=False),
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Return which content hashes are missing from CAS metadata."""

    return await service.check_project_blobs(project_id, hashes)


@router.post("/{project_id}/upload", response_model=UploadBlobResponseDTO)
async def upload_project_artifact(
    project_id: UUID,
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Upload a single artifact into CAS storage after hash verification."""

    return await service.upload_project_blob(project_id, hash, file)


@router.get("/{project_id}/artifacts/{artifact_hash}")
async def download_project_artifact(
    artifact_hash: str,
    project_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Stream a single artifact from object storage by content hash."""
    blob_stream = await service.get_project_blob_stream(project_id, artifact_hash)

    async def _iter_stream():
        try:
            for chunk in blob_stream.stream(32 * 1024):
                yield chunk
        finally:
            blob_stream.close()
            blob_stream.release_conn()

    return StreamingResponse(_iter_stream(), media_type="application/octet-stream")


@router.post("/{project_id}/snapshots", response_model=SnapshotCreateResponseDTO)
async def create_project_snapshot(
    payload: SnapshotCreateRequestDTO,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Create a snapshot that links an experiment to existing CAS artifacts."""

    return await service.create_project_snapshot(payload)


@router.get("/{project_id}/snapshots/{snapshot_id}/download")
async def download_project_snapshot(
    project_id: UUID,
    snapshot_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Stream a ZIP archive reconstructed from CAS artifacts for a snapshot."""

    zip_path, filename = await service.prepare_project_snapshot_download(
        project_id, snapshot_id
    )

    def _cleanup() -> None:
        """Delete the temporary ZIP archive after streaming completes."""

        if os.path.exists(zip_path):
            os.remove(zip_path)

    return StreamingResponse(
        open(zip_path, "rb"),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        background=BackgroundTask(_cleanup),
    )


# TODO: Add delete snapshot endpoint


@router.delete("/{project_id}", response_model=DeleteProjectResponseDTO)
async def delete_project(
    project_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Delete a project and all its artifacts and snapshots."""

    await service.delete_project(project_id)
    return DeleteProjectResponseDTO(deleted=True)


@router.delete(
    "/{project_id}/artifacts/{artifact_hash}", response_model=DeleteBlobResponseDTO
)
async def delete_project_artifact(
    artifact_hash: str,
    project_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Delete one artifact from CAS storage and tracked metadata."""

    return await service.delete_project_blob(project_id, artifact_hash)
