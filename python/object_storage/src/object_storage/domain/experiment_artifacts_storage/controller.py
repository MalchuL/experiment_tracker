"""FastAPI controller for experiment-scoped artifacts storage."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.responses import StreamingResponse

from object_storage.api.service_dependencies import get_experiment_artifacts_service
from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    TrackedUploadArtifactResponseDTO,
    UntrackedUploadArtifactResponseDTO,
)
from .service import ArtifactsStorageService

router = APIRouter(prefix="/experiment-artifacts")


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/upload-untracked",
    response_model=UntrackedUploadArtifactResponseDTO,
)
async def upload_artifact_untracked(
    project_id: UUID,
    experiment_id: UUID,
    file: UploadFile = File(...),
    hash: str | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Upload one artifact file without creating experiment metadata."""

    return await service.upload_artifact_and_forget(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=file,
        hash=hash,
    )


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/upload-tracked",
    response_model=TrackedUploadArtifactResponseDTO,
)
async def upload_artifact_tracked(
    project_id: UUID,
    experiment_id: UUID,
    file: UploadFile = File(...),
    content_type: str | None = Query(
        default=None,
        description=(
            "Optional MIME type for tracked metadata; if omitted, uses the file part's "
            "content type, then application/octet-stream."
        ),
    ),
    hash: str | None = Query(default=None),
    path: str | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Upload one artifact file and track metadata in the database."""

    return await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=file,
        content_type=content_type,
        hash=hash,
        path=path,
    )


@router.get("/projects/{project_id}/experiments/{experiment_id}/artifacts")
async def list_tracked_artifacts(
    project_id: UUID,
    experiment_id: UUID,
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """List tracked artifacts for one experiment."""

    return await service.list_artifacts(project_id, experiment_id, limit, offset)


@router.get("/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}")
async def download_artifact(
    project_id: UUID,
    experiment_id: UUID,
    artifact_hash: str,
    tracked: bool = Query(default=False),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Stream one artifact by hash for a project/experiment pair."""

    artifact = await service.get_artifact_stream(
        project_id=project_id,
        experiment_id=experiment_id,
        artifact_hash=artifact_hash,
        tracked=tracked,
    )

    async def _iter_stream():
        try:
            for chunk in artifact.stream.stream(32 * 1024):
                yield chunk
        finally:
            artifact.stream.close()
            artifact.stream.release_conn()

    headers: dict[str, str] = {}
    if artifact.filename:
        headers["Content-Disposition"] = f'attachment; filename="{artifact.filename}"'

    return StreamingResponse(
        _iter_stream(),
        media_type=artifact.mime_type,
        headers=headers,
    )


@router.delete(
    "/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}",
    response_model=DeleteArtifactResponseDTO,
)
async def delete_artifact(
    project_id: UUID,
    experiment_id: UUID,
    artifact_hash: str,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Delete one artifact for an experiment."""

    return await service.delete_artifact(project_id, experiment_id, artifact_hash)


@router.delete(
    "/projects/{project_id}/experiments/{experiment_id}",
    response_model=DeleteExperimentArtifactsResponseDTO,
)
async def delete_experiment_artifacts(
    project_id: UUID,
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    """Delete all artifacts and metadata for one experiment."""

    return await service.delete_experiment(project_id, experiment_id)
