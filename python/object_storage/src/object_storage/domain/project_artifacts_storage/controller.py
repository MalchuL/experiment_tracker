"""FastAPI controller for the CAS object storage domain."""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from object_storage.api.service_dependencies import get_project_artifacts_service
from .dto import (
    BucketListResponseDTO,
    BlobCheckResponseDTO,
    ClearStorageBucketResponseDTO,
    DeleteProjectSnapshotResponseDTO,
    DeleteStorageBucketResponseDTO,
    DeleteBlobResponseDTO,
    DeleteProjectResponseDTO,
    ProjectUsageResponseDTO,
    ReconcileStorageBucketResponseDTO,
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


@router.delete(
    "/{project_id}/snapshots/{snapshot_id}",
    response_model=DeleteProjectSnapshotResponseDTO,
)
async def delete_project_snapshot(
    project_id: UUID,
    snapshot_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    return await service.delete_project_snapshot(project_id, snapshot_id)


@router.get("/{project_id}/usage", response_model=ProjectUsageResponseDTO)
async def get_project_usage(
    project_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    return await service.get_project_usage(project_id)


@router.get("/admin/storage/buckets", response_model=BucketListResponseDTO)
async def list_storage_buckets(
    project_id: UUID | None = Query(default=None),
    experiment_id: UUID | None = Query(default=None),
    reconcile: bool = Query(
        default=False,
        description=(
            "When true, each row includes storage_size (sum of object sizes from S3/MinIO). "
            "Does not update the registry size column; use POST .../buckets/{bucket_id}/reconcile to persist."
        ),
    ),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    return await service.list_buckets(
        project_id, experiment_id, reconcile, q=q, limit=limit, offset=offset
    )


@router.delete(
    "/admin/storage/buckets/storage-only",
    response_model=DeleteStorageBucketResponseDTO,
)
async def delete_storage_only_bucket(
    name: str = Query(..., min_length=1, max_length=255),
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Remove a bucket from object storage only when it has no metadata row."""

    return await service.delete_storage_only_bucket(name)


@router.post(
    "/admin/storage/buckets/storage-only/clear",
    response_model=ClearStorageBucketResponseDTO,
)
async def clear_storage_only_bucket(
    name: str = Query(..., min_length=1, max_length=255),
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    """Delete all objects in a bucket that has no registry row (keep empty bucket)."""

    result = await service.clear_storage_only_bucket(name)
    if not result.cleared:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not clear: bucket missing, or a registry row exists "
                "(use Clear on the registered bucket instead)."
            ),
        )
    return result


@router.delete(
    "/admin/storage/buckets/{bucket_id}",
    response_model=DeleteStorageBucketResponseDTO,
)
async def delete_storage_bucket(
    bucket_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    return await service.delete_bucket(bucket_id)


@router.post(
    "/admin/storage/buckets/{bucket_id}/clear",
    response_model=ClearStorageBucketResponseDTO,
)
async def clear_storage_bucket(
    bucket_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    result = await service.clear_bucket(bucket_id)
    if not result.cleared:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return result


@router.post(
    "/admin/storage/buckets/{bucket_id}/reconcile",
    response_model=ReconcileStorageBucketResponseDTO,
)
async def reconcile_storage_bucket(
    bucket_id: UUID,
    service: ObjectStorageService = Depends(get_project_artifacts_service),
):
    return await service.reconcile_bucket(bucket_id)


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
