from __future__ import annotations

from uuid import UUID

import httpx
from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_experiment_data_service
from domain.project_artifacts.error import ProjectArtifactsNotAccessibleError
from domain.rbac.permissions import ProjectActions
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from lib.db.error import DBNotFoundError
from models import User
from starlette.responses import Response

from .dto import (
    ExperimentSnapshotDTO,
    ExperimentSnapshotFileContentDTO,
    ExperimentSnapshotFileContentRequestDTO,
    ExperimentSnapshotFilesDTO,
    ExperimentSnapshotsRequestDTO,
    ExperimentSnapshotFilesResponseDTO,
    ExperimentSnapshotUpsertDTO,
)
from .error import (
    ExperimentDataNotAccessibleError,
    ExperimentSnapshotNotFoundError,
    ExperimentDataStorageUnavailableError,
)
from .service import ExperimentDataService

router = APIRouter(prefix="/experiments", tags=["experiment-data"])


def _raise_experiment_data_http_error(error: Exception) -> None:
    """Translate domain and transport failures into FastAPI HTTP errors.

    Args:
        error: Exception raised by the experiment-data service or downstream
            object-storage HTTP client.

    Returns:
        None. This function always raises ``HTTPException`` with a status code
        suitable for the public API.
    """
    if isinstance(
        error,
        (
            ExperimentDataNotAccessibleError,
            ExperimentSnapshotNotFoundError,
            ProjectArtifactsNotAccessibleError,
            DBNotFoundError,
        ),
    ):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ExperimentDataStorageUnavailableError):
        raise HTTPException(status_code=502, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code,
            detail=error.response.text,
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Object storage unavailable")
    raise HTTPException(status_code=400, detail=str(error))


def _snapshot_download_response(
    response: httpx.Response, fallback_filename: str
) -> Response:
    """Map an upstream snapshot ZIP response to the public experiment-data response."""

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "application/zip"),
        headers={
            "Content-Disposition": response.headers.get(
                "content-disposition",
                f'attachment; filename="{fallback_filename}"',
            )
        },
    )


@router.post("/{experiment_id}/data/snapshot", response_model=ExperimentSnapshotDTO)
async def upsert_experiment_snapshot(
    experiment_id: UUID,
    payload: ExperimentSnapshotUpsertDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotDTO:
    """Create or replace the snapshot manifest for one experiment.

    Args:
        experiment_id: Experiment whose snapshot manifest should be written.
        payload: Manifest entries containing relative paths and content hashes.
        user: Authenticated user or API-token owner injected by FastAPI.
        _: Scope dependency enforcing artifact logging permission for PATs.
        service: Experiment-data service dependency.

    Returns:
        Snapshot metadata for the experiment, including the object-storage
        snapshot identifier when the upsert succeeds.
    """
    try:
        return await service.upsert_snapshot(user, experiment_id, payload.files)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.delete("/{experiment_id}/data/snapshot", response_model=ExperimentSnapshotDTO)
async def delete_experiment_snapshot(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.LOG_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotDTO:
    """Delete the current snapshot for one experiment.

    Args:
        experiment_id: Experiment whose snapshot metadata and archive should be
            removed.
        user: Authenticated user or API-token owner injected by FastAPI.
        _: Scope dependency enforcing artifact logging permission for PATs.
        service: Experiment-data service dependency.

    Returns:
        Snapshot DTO with ``snapshot_id`` cleared after successful deletion.
    """
    try:
        return await service.delete_snapshot(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.post("/data/snapshots", response_model=list[ExperimentSnapshotDTO])
async def list_experiment_snapshots(
    payload: ExperimentSnapshotsRequestDTO = Body(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> list[ExperimentSnapshotDTO]:
    """List snapshot metadata for multiple experiments in request order.

    Args:
        payload: Body containing one or more experiment IDs to resolve.
        user: Authenticated user or API-token owner injected by FastAPI.
        _: Scope dependency enforcing artifact view permission for PATs.
        service: Experiment-data service dependency.

    Returns:
        One snapshot metadata item per requested experiment ID, with missing
        snapshots represented by ``snapshot_id=None``.
    """
    try:
        return await service.list_snapshots(user, payload.experiment_ids)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.post(
    "/data/snapshots/files",
    response_model=ExperimentSnapshotFilesResponseDTO,
)
async def get_experiment_snapshot_files(
    payload: ExperimentSnapshotsRequestDTO = Body(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotFilesResponseDTO:
    """Return metadata-only file manifests from one or more experiment snapshots.

    Args:
        payload: Body containing experiment IDs whose snapshot manifests should be
            listed.
        user: Authenticated user or API-token owner injected by FastAPI.
        _: Scope dependency enforcing artifact view permission for PATs.
        service: Experiment-data service dependency.

    Returns:
        A response wrapper containing per-experiment metadata-only file entries.
    """
    try:
        items = await service.get_snapshot_files(user, payload.experiment_ids)
        return ExperimentSnapshotFilesResponseDTO(items=items)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.get(
    "/{experiment_id}/data/snapshot/files",
    response_model=ExperimentSnapshotFilesDTO,
)
async def get_experiment_snapshot_files(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotFilesDTO:
    """Return metadata-only file manifest for one experiment snapshot."""

    try:
        return await service.get_experiment_snapshot_files(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.get("/{experiment_id}/data/snapshot/download")
async def download_experiment_snapshot(
    experiment_id: UUID,
    snapshot_id: UUID | None = Query(
        default=None,
        description="Optional snapshot ID; when omitted, uses the experiment's current snapshot.",
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
):
    """Download a snapshot ZIP; defaults to the experiment's current snapshot."""

    try:
        response = await service.download_snapshot(
            user,
            experiment_id,
            snapshot_id=snapshot_id,
        )
        filename_id = snapshot_id or experiment_id
        return _snapshot_download_response(response, f"snapshot-{filename_id}.zip")
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.post(
    "/{experiment_id}/data/snapshot/file",
    response_model=ExperimentSnapshotFileContentDTO,
)
async def get_experiment_snapshot_file_content(
    experiment_id: UUID,
    payload: ExperimentSnapshotFileContentRequestDTO = Body(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotFileContentDTO:
    """Return UTF-8 content for one file in an experiment's current snapshot."""

    try:
        return await service.get_snapshot_file_content(
            user=user,
            experiment_id=experiment_id,
            path=payload.path,
            file_hash=payload.hash,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.post(
    "/{experiment_id}/data/snapshots/{snapshot_id}/file",
    response_model=ExperimentSnapshotFileContentDTO,
)
async def get_experiment_snapshot_file_content_for_snapshot(
    experiment_id: UUID,
    snapshot_id: UUID,
    payload: ExperimentSnapshotFileContentRequestDTO = Body(...),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_ARTIFACT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentSnapshotFileContentDTO:
    """Return UTF-8 content for one file in an exact current snapshot."""

    try:
        return await service.get_snapshot_file_content_for_snapshot(
            user=user,
            experiment_id=experiment_id,
            snapshot_id=snapshot_id,
            path=payload.path,
            file_hash=payload.hash,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)
