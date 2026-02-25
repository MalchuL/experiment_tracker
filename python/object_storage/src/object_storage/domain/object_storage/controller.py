"""FastAPI controller for the CAS object storage domain."""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from object_storage.db import get_async_session
from object_storage.domain.object_storage.dto import (
    BlobCheckResponseDTO,
    DeleteBlobResponseDTO,
    SnapshotCreateRequestDTO,
    SnapshotCreateResponseDTO,
    UploadBlobResponseDTO,
)
from object_storage.domain.object_storage.repository import ObjectStorageRepository
from object_storage.domain.object_storage.service import ObjectStorageService
from object_storage.storage import StorageBackend, get_storage

router = APIRouter()


def _build_service(
    session: AsyncSession, storage: StorageBackend
) -> ObjectStorageService:
    """Create a service instance wired to the current request dependencies."""

    repository = ObjectStorageRepository(session)
    return ObjectStorageService(repository, storage)


@router.post("/blobs/check", response_model=BlobCheckResponseDTO)
async def check_blobs(
    project_id: UUID = Query(...),
    hashes: list[str] = Body(..., embed=False),
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Return which content hashes are missing from CAS metadata."""

    service = _build_service(session, storage)
    return await service.check_blobs(project_id, hashes)


@router.post("/blobs/upload", response_model=UploadBlobResponseDTO)
async def upload_blob(
    project_id: UUID = Query(...),
    hash: str = Query(..., min_length=64, max_length=64),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Upload a single blob into CAS storage after hash verification."""

    service = _build_service(session, storage)
    return await service.upload_blob(project_id, hash, file)


@router.get("/blobs/{blob_hash}")
async def download_blob(
    blob_hash: str,
    project_id: UUID = Query(...),
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Stream a single blob from object storage by content hash."""
    service = _build_service(session, storage)
    blob_stream = await service.get_blob_stream(project_id, blob_hash)

    async def _iter_stream():
        try:
            for chunk in blob_stream.stream(32 * 1024):
                yield chunk
        finally:
            blob_stream.close()
            blob_stream.release_conn()

    return StreamingResponse(_iter_stream(), media_type="application/octet-stream")


@router.post("/snapshots", response_model=SnapshotCreateResponseDTO)
async def create_snapshot(
    payload: SnapshotCreateRequestDTO,
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Create a snapshot that links an experiment to existing CAS blobs."""

    service = _build_service(session, storage)
    return await service.create_snapshot(payload)


@router.get("/snapshots/{snapshot_id}/download")
async def download_snapshot(
    project_id: UUID,
    snapshot_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Stream a ZIP archive reconstructed from CAS blobs for a snapshot."""

    service = _build_service(session, storage)
    zip_path, filename = await service.prepare_snapshot_download(
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


@router.delete("/blobs/{blob_hash}", response_model=DeleteBlobResponseDTO)
async def delete_blob(
    blob_hash: str,
    project_id: UUID = Query(...),
    session: AsyncSession = Depends(get_async_session),
    storage: StorageBackend = Depends(get_storage),
):
    """Delete one blob from CAS storage and tracked metadata."""

    service = _build_service(session, storage)
    return await service.delete_blob(project_id, blob_hash)
