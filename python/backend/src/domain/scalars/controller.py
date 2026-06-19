"""HTTP routes under ``/scalars``: log and query time-series via the scalars satellite service."""

from uuid import UUID
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from clients.scalars import (
    GetScalarsResponseDTO,
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResponseDTO,
    LogScalarsBatchRequestDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    ScalarsSampling,
)
from domain.rbac.permissions import ProjectActions
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User

from .error import ScalarsNotAccessibleError
from .service import ScalarsServiceProtocol
from api.routes.service_dependencies import get_scalars_service

router = APIRouter(prefix="/scalars", tags=["scalars"])


def _raise_scalars_http_error(error: Exception) -> None:
    """Map scalars access errors and HTTP client failures to API responses.

    Args:
        error: Exception raised by ``ScalarsServiceProtocol`` or the scalars HTTP
            client.

    Raises:
        HTTPException: ``403`` for RBAC denial, upstream status codes for scalars
            ``HTTPStatusError``, ``502`` when the satellite is unavailable, and
            ``400`` for other errors.
    """
    if isinstance(error, ScalarsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        detail = error.response.text
        raise HTTPException(status_code=status, detail=detail)
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Scalars service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


@router.post("/log/{experiment_id}", response_model=LogScalarResponseDTO)
async def log_scalar(
    experiment_id: UUID,
    data: LogScalarRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Log one scalar point for an experiment.

    Args:
        experiment_id: Experiment that owns the scalar row.
        data: Scalar metric payload.
        user: Authenticated user logging the scalar.
        _: API-token scope guard requiring metric creation access.
        scalars_service: Scalars service dependency.

    Returns:
        LogScalarResponseDTO: Satellite logging result.

    Raises:
        HTTPException: ``403`` for permission denial, upstream scalars status codes,
            ``502`` for satellite unavailability, or ``400`` for other errors.
    """
    try:
        return await scalars_service.log_scalar(user, experiment_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.post(
    "/log_batch/{experiment_id}",
    response_model=LogScalarResponseDTO,
)
async def log_scalars_batch(
    experiment_id: UUID,
    data: LogScalarsBatchRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Log a batch of scalar points for an experiment.

    Args:
        experiment_id: Experiment that owns the scalar rows.
        data: Batch scalar payload.
        user: Authenticated user logging scalars.
        _: API-token scope guard requiring metric creation access.
        scalars_service: Scalars service dependency.

    Returns:
        LogScalarResponseDTO: Satellite batch logging result.

    Raises:
        HTTPException: ``403`` for permission denial, upstream scalars status codes,
            ``502`` for satellite unavailability, or ``400`` for other errors.
    """
    try:
        return await scalars_service.log_scalars_batch(user, experiment_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/{experiment_id}", response_model=GetScalarsResponseDTO)
async def get_scalars(
    experiment_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    max_points: int | None = Query(default=None, ge=1),
    sampling: ScalarsSampling = Query(default=ScalarsSampling.UNIFORM),
    columns_per_query: int = Query(default=1, ge=1, le=32),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    start_step: int | None = Query(default=None),
    end_step: int | None = Query(default=None),
    scalar_name: list[str] | None = Query(default=None),
    store_cache: bool = Query(default=True),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Query scalar series for one experiment.

    Args:
        experiment_id: Experiment identifier.
        limit: Maximum number of experiment groups to return.
        offset: Number of experiment groups to skip.
        max_points: Optional sampling target per metric column.
        sampling: Sampling algorithm requested from scalars.
        columns_per_query: Number of columns the satellite may query concurrently.
        return_tags: Whether tag metadata should be included.
        start_time: Optional lower timestamp bound.
        end_time: Optional upper timestamp bound.
        user: Authenticated user requesting scalars.
        _: API-token scope guard requiring metric view access.
        scalars_service: Scalars service dependency.

    Returns:
        GetScalarsResponseDTO: Paginated scalar series payload.

    Raises:
        HTTPException: ``403`` for permission denial, upstream scalars status codes,
            ``502`` for satellite unavailability, or ``400`` for query errors.
    """
    try:
        return await scalars_service.get_scalars_for_experiment(
            user,
            experiment_id,
            list_options=ListOptions(limit=limit, offset=offset),
            max_points=max_points,
            sampling=sampling,
            columns_per_query=columns_per_query,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
            start_step=start_step,
            end_step=end_step,
            scalar_names=scalar_name,
            store_cache=store_cache,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/project/{project_id}", response_model=GetScalarsResponseDTO)
async def get_project_scalars(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    max_points: int | None = Query(default=None, ge=1),
    sampling: ScalarsSampling = Query(default=ScalarsSampling.UNIFORM),
    columns_per_query: int = Query(default=1, ge=1, le=32),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    start_step: int | None = Query(default=None),
    end_step: int | None = Query(default=None),
    scalar_name: list[str] | None = Query(default=None),
    store_cache: bool = Query(default=True),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Query scalar series for a project and optional experiment filter.

    Args:
        project_id: Project identifier.
        experiment_id: Optional repeated query parameter of experiment ids.
        limit: Maximum number of experiment groups to return.
        offset: Number of experiment groups to skip.
        max_points: Optional sampling target per metric column.
        sampling: Sampling algorithm requested from scalars.
        columns_per_query: Number of columns the satellite may query concurrently.
        return_tags: Whether tag metadata should be included.
        start_time: Optional lower timestamp bound.
        end_time: Optional upper timestamp bound.
        user: Authenticated user requesting scalars.
        _: API-token scope guard requiring metric view access.
        scalars_service: Scalars service dependency.

    Returns:
        GetScalarsResponseDTO: Paginated scalar series payload.

    Raises:
        HTTPException: ``403`` for permission denial, upstream scalars status codes,
            ``502`` for satellite unavailability, or ``400`` for query errors.
    """
    try:
        return await scalars_service.get_scalars(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            list_options=ListOptions(limit=limit, offset=offset),
            max_points=max_points,
            sampling=sampling,
            columns_per_query=columns_per_query,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
            start_step=start_step,
            end_step=end_step,
            scalar_names=scalar_name,
            store_cache=store_cache,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/names/project/{project_id}")
async def get_project_scalar_names(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Return known scalar names for a project without loading scalar point values."""
    try:
        return await scalars_service.get_scalar_names(user=user, project_id=project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.post(
    "/last_logged/{project_id}",
    response_model=LastLoggedExperimentsResponseDTO,
)
async def get_last_logged_experiments(
    project_id: UUID,
    payload: LastLoggedExperimentsRequestDTO,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    """Return last-logged scalar timestamps for project experiments.

    Args:
        project_id: Project identifier.
        payload: Optional experiment filter payload.
        limit: Maximum number of experiment rows to return.
        offset: Number of experiment rows to skip.
        user: Authenticated user requesting metadata.
        _: API-token scope guard requiring metric view access.
        scalars_service: Scalars service dependency.

    Returns:
        LastLoggedExperimentsResponseDTO: Paginated last-logged rows.

    Raises:
        HTTPException: ``403`` for permission denial, upstream scalars status codes,
            ``502`` for satellite unavailability, or ``400`` for query errors.
    """
    try:
        return await scalars_service.get_last_logged_experiments(
            user=user,
            project_id=project_id,
            experiment_ids=payload.experiment_ids,
            list_options=ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)
