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
    ExperimentHparamsDTO,
    ExperimentHparamsUpsertDTO,
)
from .error import (
    ExperimentDataNotAccessibleError,
    ExperimentSnapshotNotFoundError,
    ExperimentDataStorageUnavailableError,
)
from .service import ExperimentDataService

router = APIRouter(
    prefix="/experiments",
    tags=["experiment-data"],
)


@router.get("/{experiment_id}/hparams", response_model=ExperimentHparamsDTO)
async def get_experiment_hparams(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentHparamsDTO:
    try:
        return await service.get_hparams(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.put("/{experiment_id}/hparams", response_model=ExperimentHparamsDTO)
async def upsert_experiment_hparams(
    experiment_id: UUID,
    payload: ExperimentHparamsUpsertDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_EXPERIMENT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentHparamsDTO:
    try:
        return await service.upsert_hparams(user, experiment_id, payload.hparams)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


@router.delete("/{experiment_id}/hparams", response_model=ExperimentHparamsDTO)
async def delete_experiment_hparams(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_EXPERIMENT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentHparamsDTO:
    try:
        return await service.delete_hparams(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)


def _raise_experiment_data_http_error(error: Exception) -> None:
    """Map experiment-data and object-storage failures to HTTP status codes.

    Purpose:
        Keeps route handlers thin: domain ``404``/``502`` types and ``httpx`` errors
        from the storage client become consistent FastAPI responses for the web BFF
        and SDK.

    Args:
        error: Any exception bubbled out of a service call.

    Raises:
        HTTPException: Always raised; never returns normally.
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
    """Wrap object-storage ZIP bytes as a browser-friendly attachment response.

    Purpose:
        ``download_snapshot`` returns a raw ``httpx.Response``; this helper copies
        body, ``Content-Type``, and ``Content-Disposition`` (with a safe fallback
        filename) for experiment snapshot download routes.

    Args:
        response: Upstream ZIP response from project-artifacts / object storage.
        fallback_filename: Used when upstream omits ``Content-Disposition``.

    Returns:
        Starlette ``Response`` suitable for FastAPI to return to clients.
    """
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
    """Log or replace an experiment's code snapshot manifest (SDK / training).

    Purpose:
        Primary write entry point after files are uploaded to project CAS. Stores
        the new snapshot UUID on the experiment and replaces any previous archive.

    Args:
        experiment_id: Experiment receiving the manifest.
        payload: Full file list (path + hash per entry).
        user: Session user or API token.
        _: PAT scope guard (``LOG_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        ``ExperimentSnapshotDTO`` with the new ``snapshot_id``.

    Raises:
        HTTPException: Via :func:`_raise_experiment_data_http_error` on failure.
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
    """Delete the experiment's current code snapshot from storage and metadata.

    Purpose:
        Removes the archive and clears the ``ExperimentData`` snapshot pointer so
        the experiment no longer appears in file-compare or download flows.

    Args:
        experiment_id: Experiment to clear.
        user: Session user or API token.
        _: PAT scope guard (``LOG_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        Snapshot DTO with ``snapshot_id=None``.

    Raises:
        HTTPException: ``404`` when no snapshot exists; other codes from the mapper.
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
    """Bulk-read snapshot IDs for compare selection and dashboards.

    Purpose:
        ``POST /experiments/data/snapshots`` resolves many experiments in one round
        trip without loading per-file manifests—only ``snapshot_id`` and row metadata.

    Args:
        payload: ``experiment_ids`` list (order preserved in the response).
        user: Session user or API token.
        _: PAT scope guard (``VIEW_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        List of ``ExperimentSnapshotDTO`` aligned with the request order.

    Raises:
        HTTPException: Authorization or storage failures per experiment.
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
    """Bulk-read file trees (path, hash, size) for multi-experiment file compare.

    Purpose:
        ``POST /experiments/data/snapshots/files`` feeds the compare page when several
        experiments are selected: builds left/right trees and diff badges without
        downloading file bodies.

    Args:
        payload: ``experiment_ids`` to list manifests for.
        user: Session user or API token.
        _: PAT scope guard (``VIEW_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        ``ExperimentSnapshotFilesResponseDTO`` with one manifest item per experiment.

    Raises:
        HTTPException: On permission or upstream storage errors.
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
    """Read the current snapshot file tree for one experiment.

    Purpose:
        ``GET .../data/snapshot/files`` supports compare UI when a single side's
        experiment changes—lighter than the bulk POST and cache-friendly per
        experiment ID.

    Args:
        experiment_id: Experiment whose manifest is listed.
        user: Session user or API token.
        _: PAT scope guard (``VIEW_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        ``ExperimentSnapshotFilesDTO`` (empty ``files`` if no snapshot logged).

    Raises:
        HTTPException: On permission or storage errors.
    """
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
    """Download an experiment code snapshot as a ZIP attachment.

    Purpose:
        Used by the experiment sidebar and compare tab "Download snapshot" actions.
        Optional ``snapshot_id`` query param downloads a specific archive UUID; omit
        it to use the experiment's current pointer from metadata.

    Args:
        experiment_id: Experiment context for RBAC and default snapshot resolution.
        snapshot_id: Optional explicit archive UUID (no "must match current" check).
        user: Session user or API token.
        _: PAT scope guard (``VIEW_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        ZIP file ``Response`` with ``Content-Disposition`` attachment headers.

    Raises:
        HTTPException: ``404`` when no snapshot is available for download.
    """
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
    """Preview one UTF-8 text file from the experiment's current snapshot.

    Purpose:
        Server-side text preview for API clients that send manifest ``path`` and
        ``hash`` together. Validates the pair against the logged snapshot, then
        returns decoded content. The web compare UI typically downloads CAS blobs
        by hash instead; this route is kept for future features and non-browser
        consumers.

    Args:
        experiment_id: Experiment whose *current* snapshot is read.
        payload: ``path`` and ``hash`` identifying one manifest entry.
        user: Session user or API token.
        _: PAT scope guard (``VIEW_ARTIFACT``).
        service: Injected :class:`ExperimentDataService`.

    Returns:
        ``ExperimentSnapshotFileContentDTO`` with UTF-8 ``content``.

    Raises:
        HTTPException: ``404`` for missing snapshot, unknown file, or non-UTF-8 data.
    """
    try:
        return await service.get_snapshot_file_content(
            user=user,
            experiment_id=experiment_id,
            path=payload.path,
            file_hash=payload.hash,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_data_http_error(exc)
