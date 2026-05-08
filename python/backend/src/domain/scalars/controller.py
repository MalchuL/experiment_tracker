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
    """Map scalars access errors and HTTP client failures to API responses."""
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
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
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
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
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
        )
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
    try:
        return await scalars_service.get_last_logged_experiments(
            user=user,
            project_id=project_id,
            experiment_ids=payload.experiment_ids,
            list_options=ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)
