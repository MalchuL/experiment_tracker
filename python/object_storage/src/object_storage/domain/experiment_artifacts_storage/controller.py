"""FastAPI controller for experiment-scoped artifacts storage."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from starlette.responses import StreamingResponse

from object_storage.api.service_dependencies import get_experiment_artifacts_service
from .dto import (
    DeleteArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
    ExperimentArtifactsUsageResponseDTO,
    TrackedArtifactsListResponseDTO,
    TrackedArtifactInfoResponseDTO,
    TrackedUploadArtifactResponseDTO,
    UntrackedUploadArtifactResponseDTO,
)
from .service import ArtifactsStorageService

router = APIRouter(prefix="/experiment-artifacts")


def _parse_metadata_query(raw: str | None) -> dict[str, Any] | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="metadata must be valid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")
    return parsed


@router.post(
    "/projects/{project_id}/experiments/{experiment_id}/upload-untracked",
    response_model=UntrackedUploadArtifactResponseDTO,
)
async def upload_artifact_untracked(
    project_id: UUID,
    experiment_id: UUID,
    file: UploadFile = File(...),
    artifact_hash: str | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> UntrackedUploadArtifactResponseDTO:
    """
    Upload one artifact file without creating experiment metadata.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.
        file: The upload file.
        artifact_hash: The hash of the artifact that used to store in storage.

    Returns:
        The response from the object storage.
        The response contains the hash and size of the uploaded artifact.
    """

    return await service.upload_artifact_and_forget(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=file,
        artifact_hash=artifact_hash,
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
    artifact_hash: str | None = Query(default=None),
    file_path: str | None = Query(default=None),
    metadata: str | None = Query(
        default=None,
        description=(
            r'Optional JSON object stored on the blob row as-is, e.g. {"name": "weights"}. '
            "Omitted or empty means ``{}``."
        ),
    ),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> TrackedUploadArtifactResponseDTO:
    """
    Upload one artifact file and track metadata in the database.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.
        file: The upload file.
        content_type: Optional MIME type for the tracked row; when omitted or blank,
            uses the upload part's content type, then ``application/octet-stream``.
        artifact_hash: The hash of the artifact that used to store in storage.
        file_path: Relative path for the tracked blob (stored on the row).
        metadata: Optional JSON object stored as-is on the blob row (default ``{}``).

    Returns:
        The response from the object storage.
        The response contains the hash and size of the uploaded artifact.
    """

    return await service.upload_artifact_and_track(
        project_id=project_id,
        experiment_id=experiment_id,
        upload=file,
        content_type=content_type,
        artifact_hash=artifact_hash,
        file_path=file_path,
        metadata=_parse_metadata_query(metadata),
    )


@router.get(
    "/projects/{project_id}/experiments/{experiment_id}/artifacts",
    response_model=TrackedArtifactsListResponseDTO,
)
async def list_tracked_artifacts(
    project_id: UUID,
    experiment_id: UUID,
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
    file_path: list[str] | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> TrackedArtifactsListResponseDTO:
    """List tracked artifacts for one experiment.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.
        limit: The maximum number of artifacts to return.
        offset: The offset of the artifacts to return.
    Returns:
        The response from the object storage.
        The response contains the list of tracked artifacts.
    """

    return await service.list_artifacts(
        project_id,
        experiment_id,
        limit,
        offset,
        file_paths=file_path,
    )


@router.get(
    "/projects/{project_id}/experiments/{experiment_id}/artifacts/info",
    response_model=TrackedArtifactInfoResponseDTO,
)
async def get_tracked_artifact_info(
    project_id: UUID,
    experiment_id: UUID,
    file_path: str | None = Query(default=None),
    blob_id: UUID | None = Query(default=None),
    artifact_hash: str | None = Query(default=None),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> TrackedArtifactInfoResponseDTO:
    """Return tracked artifact DB metadata by filepath, row id, or artifact hash."""
    try:
        return await service.get_tracked_artifact_info(
            project_id=project_id,
            experiment_id=experiment_id,
            file_path=file_path,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc


@router.get(
    "/projects/{project_id}/experiments/{experiment_id}/usage",
    response_model=ExperimentArtifactsUsageResponseDTO,
)
async def get_experiment_artifacts_usage(
    project_id: UUID,
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
):
    return await service.get_experiment_usage(project_id, experiment_id)


@router.get(
    "/projects/{project_id}/experiments/{experiment_id}/artifacts/{artifact_hash}"
)
async def download_artifact(
    project_id: UUID,
    experiment_id: UUID,
    artifact_hash: str,
    tracked: bool = Query(default=False),
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> StreamingResponse:
    """Stream one artifact by hash for a project/experiment pair.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.
        artifact_hash: The hash of the artifact.
        tracked: Whether the artifact is tracked.
    Returns:
        The response from the object storage.
        The response contains the streamed artifact.
    """

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
) -> DeleteArtifactResponseDTO:
    """Delete one artifact for an experiment.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.
        artifact_hash: The hash of the artifact.
    Returns:
        The response from the object storage.
        The response contains the deleted artifact.
    """

    return await service.delete_artifact(project_id, experiment_id, artifact_hash)


@router.delete(
    "/projects/{project_id}/experiments/{experiment_id}/cleanup-tracked",
    response_model=DeleteExperimentArtifactsResponseDTO,
)
async def cleanup_tracked_experiment_artifacts(
    project_id: UUID,
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete tracked experiment artifacts only (metadata + those blob keys)."""

    return await service.delete_tracked_experiment_artifacts(project_id, experiment_id)


@router.delete(
    "/projects/{project_id}/experiments/{experiment_id}/cleanup-untracked",
    response_model=DeleteExperimentArtifactsResponseDTO,
)
async def cleanup_untracked_experiment_blobs(
    project_id: UUID,
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete storage objects not referenced by tracked experiment artifact rows."""

    return await service.delete_untracked_experiment_blobs(project_id, experiment_id)


@router.delete(
    "/projects/{project_id}/experiments/{experiment_id}",
    response_model=DeleteExperimentArtifactsResponseDTO,
)
async def delete_experiment_artifacts(
    project_id: UUID,
    experiment_id: UUID,
    service: ArtifactsStorageService = Depends(get_experiment_artifacts_service),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete all artifacts and metadata for one experiment.

    Args:
        project_id: The ID of the project.
        experiment_id: The ID of the experiment.

    Returns:
        The response from the object storage.
        The response contains the number of deleted artifacts.
    """

    return await service.delete_experiment(project_id, experiment_id)
