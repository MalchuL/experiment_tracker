"""Experiment artifacts controller: log, upload, download, delete."""

from experiment_tracker_shared.datetime_utc import to_json_utc_z
import json
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from clients.artifacts_info import (
    ArtifactType,
    ArtifactsInfoResultDTO,
    ArtifactsInfoSummaryResultDTO,
    LogArtifactResponseDTO as ArtifactsInfoLogArtifactResponseDTO,
)
from clients.object_storage import (
    DeleteExperimentArtifactResponseDTO,
    DeleteExperimentArtifactsResponseDTO,
)
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_experiment_artifacts_service
from domain.rbac.permissions import ProjectActions
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User

from .dto import (
    ExperimentArtifactDTO,
    ExperimentArtifactListResponseDTO,
)
from .error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactAmbiguousError,
    ExperimentArtifactNotFoundError,
)
from .protocol import ExperimentArtifactsServiceProtocol

router = APIRouter(prefix="/experiment-artifacts", tags=["experiment-artifacts"])


def _raise_http_error(error: Exception) -> None:
    """Translate experiment-artifact service/client errors to HTTP responses.

    Args:
        error: Exception raised by the experiment-artifact service, artifacts-info
            client, or object-storage client.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing artifacts,
            ``400`` for ambiguous artifacts or validation errors, upstream status
            codes for HTTP client errors, and ``502`` when a satellite is unavailable.
    """
    if isinstance(error, ExperimentArtifactsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ExperimentArtifactNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ExperimentArtifactAmbiguousError):
        raise HTTPException(status_code=400, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code,
            detail=error.response.text,
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(
            status_code=502,
            detail="Experiment artifacts service unavailable",
        )
    raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentArtifactListResponseDTO,
)
async def list_experiment_artifacts(
    experiment_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    file_paths: list[str] | None = Query(
        default=None,
        description="Filter by exact stored file_path (repeat param for multiple values).",
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactListResponseDTO:
    """List tracked artifacts for one experiment.

    Args:
        experiment_id: Experiment whose tracked artifacts should be listed.
        limit: Maximum number of artifacts to return.
        offset: Number of artifacts to skip.
        file_paths: Optional exact stored path filter; repeated query params allowed.
        user: Authenticated user requesting artifacts.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        ExperimentArtifactListResponseDTO: Paginated tracked artifact metadata.

    Raises:
        HTTPException: Mapped access, not-found, satellite, and validation errors.
    """
    try:
        return await service.list_experiment_artifacts(
            user=user,
            experiment_id=experiment_id,
            list_options=ListOptions(limit=limit, offset=offset),
            file_paths=file_paths,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


# TODO move to post
@router.get("/projects/{project_id}/get-at-step")
async def get_experiments_artifacts_at_step(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[ArtifactType] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    step: list[int] | None = Query(default=None),
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoResultDTO:
    """List at-step artifact metadata rows for a project.

    Args:
        project_id: Project whose artifacts-info table should be queried.
        experiment_id: Optional repeated experiment filter.
        artifact_type: Optional repeated artifact type filter.
        artifact_name: Optional repeated artifact name filter.
        step: Optional repeated training-step filter.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
        start_time: Optional lower timestamp bound.
        end_time: Optional upper timestamp bound.
        user: Authenticated user requesting artifacts.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        ArtifactsInfoResultDTO: Paginated artifacts-info rows.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    try:
        result = await service.get_experiments_artifacts_at_step(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            artifact_types=artifact_type,
            artifact_names=artifact_name,
            steps=step,
            list_options=ListOptions(limit=limit, offset=offset),
            start_time=to_json_utc_z(start_time) if start_time else None,
            end_time=to_json_utc_z(end_time) if end_time else None,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/projects/{project_id}/summary-at-step")
async def get_experiments_artifacts_summary_at_step(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    artifact_type: list[ArtifactType] | None = Query(default=None),
    artifact_name: list[str] | None = Query(default=None),
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    max_steps: int = Query(default=1000, ge=1),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoSummaryResultDTO:
    """List at-step artifact summaries for slider construction.

    Args:
        project_id: Project whose artifacts should be summarized.
        experiment_id: Optional repeated experiment filter.
        artifact_type: Optional repeated artifact type filter.
        artifact_name: Optional repeated artifact name filter.
        limit: Maximum number of summary groups to return.
        offset: Number of summary groups to skip.
        max_steps: Maximum step values per artifact summary.
        start_time: Optional lower timestamp bound.
        end_time: Optional upper timestamp bound.
        user: Authenticated user requesting summaries.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        ArtifactsInfoSummaryResultDTO: Lightweight artifact summary groups.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    try:
        return await service.get_experiments_artifacts_summary_at_step(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            artifact_types=artifact_type,
            artifact_names=artifact_name,
            list_options=ListOptions(limit=limit, offset=offset),
            max_steps=max_steps,
            start_time=to_json_utc_z(start_time) if start_time else None,
            end_time=to_json_utc_z(end_time) if end_time else None,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/projects/{project_id}/get-at-step/detail")
async def get_experiment_artifact_detail_at_step(
    project_id: UUID,
    experiment_id: UUID = Query(...),
    artifact_name: str = Query(..., min_length=1),
    step: int = Query(...),
    artifact_type: ArtifactType | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoResultDTO:
    """Return one full at-step artifact metadata row.

    Args:
        project_id: Project that owns the artifacts-info table.
        experiment_id: Experiment identifier.
        artifact_name: Artifact name selected from a summary.
        step: Training step selected from a summary.
        artifact_type: Optional artifact type disambiguator.
        user: Authenticated user requesting details.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        ArtifactsInfoResultDTO: Detail row payload from artifacts-info.

    Raises:
        HTTPException: Mapped access, not-found, satellite, and validation errors.
    """
    try:
        return await service.get_experiment_artifact_detail_at_step(
            user=user,
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_name=artifact_name,
            step=step,
            artifact_type=artifact_type,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post(
    "/{experiment_id}/log-at-step",
    response_model=ArtifactsInfoLogArtifactResponseDTO,
)
async def upload_and_log_experiment_artifact_at_step(
    experiment_id: UUID,
    file: UploadFile = File(...),
    name: str = Form(...),
    artifact_type: ArtifactType = Form(...),
    step: int = Form(...),
    metadata: str | None = Form(None),
    tags: str | None = Form(None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ArtifactsInfoLogArtifactResponseDTO:
    """Upload a file and log at-step artifact metadata.

    Args:
        experiment_id: Experiment receiving the artifact.
        file: Multipart file stream.
        name: Artifact display name.
        artifact_type: Artifact type used by UI renderers.
        step: Training step associated with the artifact.
        metadata: Optional JSON string or raw string metadata.
        tags: Optional JSON array string or comma-separated tags.
        user: Authenticated user logging the artifact.
        _: API-token scope guard requiring artifact logging access.
        service: Experiment-artifacts service dependency.

    Returns:
        ArtifactsInfoLogArtifactResponseDTO: Artifacts-info logging result.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    metadata_dict: dict[str, str] | None = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {"raw": metadata}
    tags_list: list[str] | None = None
    if tags:
        try:
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        return await service.upload_and_log_experiment_artifact_at_step(
            user=user,
            experiment_id=experiment_id,
            file=file,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata_dict,
            tags=tags_list,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/{experiment_id}/download-at-step")
async def download_experiment_artifact_at_step(
    experiment_id: UUID,
    step: int = Query(...),
    name: str = Query(..., min_length=1),
    artifact_type: ArtifactType | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download artifact bytes for a logged step/name.

    Args:
        experiment_id: Experiment that owns the logged artifact.
        step: Training step.
        name: Artifact name.
        artifact_type: Optional type disambiguator.
        user: Authenticated user requesting bytes.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        Response: Binary response with content type and download filename.

    Raises:
        HTTPException: Mapped access, not-found, ambiguous, satellite, and validation
            errors.
    """
    try:
        payload = await service.download_experiment_artifact_at_step(
            user=user,
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )
        disposition = f"attachment; filename*=UTF-8''{quote(payload.filename, safe='')}"
        return Response(
            content=payload.content,
            media_type=payload.content_type,
            headers={"Content-Disposition": disposition},
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{experiment_id}/at-step")
async def delete_experiment_artifact_by_hash(
    experiment_id: UUID,
    hash: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactResponseDTO:
    """Delete one experiment artifact by content hash.

    Args:
        experiment_id: Experiment whose artifact should be removed.
        hash: Artifact content hash/path.
        user: Authenticated user deleting the artifact.
        _: API-token scope guard requiring artifact logging access.
        service: Experiment-artifacts service dependency.

    Returns:
        DeleteExperimentArtifactResponseDTO: Object-storage deletion result.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    try:
        result = await service.delete_experiment_artifact_by_hash(
            user=user, experiment_id=experiment_id, hash=hash
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/{experiment_id}/all")
async def delete_experiment_all_artifacts(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactsResponseDTO:
    """Delete all tracked and untracked artifacts for an experiment.

    Args:
        experiment_id: Experiment whose artifact bucket should be cleaned.
        user: Authenticated user deleting artifacts.
        _: API-token scope guard requiring artifact logging access.
        service: Experiment-artifacts service dependency.

    Returns:
        DeleteExperimentArtifactsResponseDTO: Object-storage bulk deletion result.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    try:
        result = await service.delete_experiment_all_artifacts(
            user=user, experiment_id=experiment_id
        )
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.post("/upsert", response_model=ExperimentArtifactDTO)
async def upsert_experiment_artifact(
    experiment_id: UUID = Form(...),
    name: str | None = Form(default=None),
    filepath: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactDTO:
    """Upsert one tracked artifact metadata row and object payload.

    If a tracked artifact already exists at ``filepath``, the service deletes it and
    uploads the replacement file. Otherwise it creates a new tracked artifact.

    Args:
        experiment_id: Experiment receiving the tracked artifact.
        name: Optional display name stored in artifact metadata.
        filepath: Relative artifact path in object storage.
        file: Multipart file stream.
        user: Authenticated user uploading the artifact.
        _: API-token scope guard requiring artifact logging access.
        service: Experiment-artifacts service dependency.

    Returns:
        ExperimentArtifactDTO: Tracked artifact metadata for the stored file.

    Raises:
        HTTPException: Mapped access, satellite, and validation errors.
    """
    try:
        return await service.upsert_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            name=name,
            filepath=filepath,
            file=file,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/get", response_model=ExperimentArtifactDTO)
async def get_experiment_artifact(
    experiment_id: UUID,
    filepath: str | None = Query(default=None, min_length=1),
    blob_id: UUID | None = Query(default=None),
    artifact_hash: str | None = Query(default=None, min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> ExperimentArtifactDTO:
    """Get one tracked artifact metadata row.

    Args:
        experiment_id: Experiment that owns the artifact.
        filepath: Optional relative path identifier.
        blob_id: Optional blob identifier.
        artifact_hash: Optional content hash identifier.
        user: Authenticated user requesting metadata.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        ExperimentArtifactDTO: Matching tracked artifact metadata.

    Raises:
        HTTPException: ``400`` if no identifier is supplied, plus mapped access,
            not-found, and satellite errors.
    """
    try:
        return await service.get_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.delete("/delete")
async def delete_experiment_tracked_artifact(
    experiment_id: UUID,
    filepath: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
) -> DeleteExperimentArtifactResponseDTO:
    """Delete one tracked artifact by filepath.

    Args:
        experiment_id: Experiment that owns the artifact.
        filepath: Relative tracked artifact path.
        user: Authenticated user deleting the artifact.
        _: API-token scope guard requiring artifact logging access.
        service: Experiment-artifacts service dependency.

    Returns:
        DeleteExperimentArtifactResponseDTO: Object-storage deletion result.

    Raises:
        HTTPException: Mapped access, not-found, satellite, and validation errors.
    """
    try:
        return await service.delete_experiment_tracked_artifact(
            user=user,
            experiment_id=experiment_id,
            filepath=filepath,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/download")
async def download_experiment_artifact(
    experiment_id: UUID,
    filepath: str | None = Query(default=None, min_length=1),
    blob_id: UUID | None = Query(default=None),
    artifact_hash: str | None = Query(default=None, min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download one tracked artifact by filepath, blob id, or hash.

    Args:
        experiment_id: Experiment that owns the artifact.
        filepath: Optional relative path identifier.
        blob_id: Optional blob identifier.
        artifact_hash: Optional content hash identifier.
        user: Authenticated user requesting bytes.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        Response: Binary response with content type and download filename.

    Raises:
        HTTPException: ``400`` if no identifier is supplied, plus mapped access,
            not-found, and satellite errors.
    """
    try:
        payload = await service.download_experiment_artifact(
            user=user,
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        disposition = f"attachment; filename*=UTF-8''{quote(payload.filename, safe='')}"
        return Response(
            content=payload.content,
            media_type=payload.content_type,
            headers={"Content-Disposition": disposition},
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)


@router.get("/download/archive")
async def download_experiment_artifacts_archive(
    experiment_id: UUID,
    name: str = Query(..., min_length=1),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentArtifactsServiceProtocol = Depends(
        get_experiment_artifacts_service
    ),
):
    """Download tracked artifacts sharing a display name as a ZIP archive.

    Args:
        experiment_id: Experiment that owns the tracked artifacts.
        name: Artifact display name stored in metadata.
        user: Authenticated user requesting the archive.
        _: API-token scope guard requiring artifact view access.
        service: Experiment-artifacts service dependency.

    Returns:
        StreamingResponse: ZIP archive stream with background temp-file cleanup.

    Raises:
        HTTPException: Mapped access, not-found, satellite, and archive creation
            errors.
    """
    try:
        archive_path, filename = await service.download_experiment_artifacts_archive(
            user=user,
            experiment_id=experiment_id,
            name=name,
        )

        def _cleanup() -> None:
            import os

            if os.path.exists(archive_path):
                os.remove(archive_path)

        return StreamingResponse(
            open(archive_path, "rb"),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            background=BackgroundTask(_cleanup),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_http_error(exc)
