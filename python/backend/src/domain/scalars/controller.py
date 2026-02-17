from uuid import UUID
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from domain.rbac.permissions import ProjectActions
from models import User

from .dto import (
    LastLoggedExperimentsRequestDTO,
    LastLoggedExperimentsResultDTO,
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    LogScalarsRequestDTO,
    LogScalarsResponseDTO,
    ScalarsPointsResultDTO,
)
from .error import ScalarsNotAccessibleError
from .service import ScalarsServiceProtocol
from api.routes.service_dependencies import get_scalars_service

router = APIRouter(prefix="/scalars", tags=["scalars"])


def _raise_scalars_http_error(error: Exception) -> None:
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
        result = await scalars_service.log_scalar(user, experiment_id, data.model_dump())
        return LogScalarResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.post(
    "/log_batch/{experiment_id}",
    response_model=LogScalarsResponseDTO,
)
async def log_scalars_batch(
    experiment_id: UUID,
    data: LogScalarsRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    try:
        result = await scalars_service.log_scalars_batch(
            user, experiment_id, data.model_dump()
        )
        return LogScalarsResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/{experiment_id}", response_model=ScalarsPointsResultDTO)
async def get_scalars(
    experiment_id: UUID,
    max_points: int | None = Query(default=None, ge=1),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    try:
        result = await scalars_service.get_scalars_for_experiment(
            user,
            experiment_id,
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
        )
        return ScalarsPointsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/project/{project_id}", response_model=ScalarsPointsResultDTO)
async def get_project_scalars(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    max_points: int | None = Query(default=None, ge=1),
    return_tags: bool = Query(default=False),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    try:
        result = await scalars_service.get_scalars(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
        )
        return ScalarsPointsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.post(
    "/last_logged/{project_id}",
    response_model=LastLoggedExperimentsResultDTO,
)
async def get_last_logged_experiments(
    project_id: UUID,
    payload: LastLoggedExperimentsRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    try:
        result = await scalars_service.get_last_logged_experiments(
            user=user,
            project_id=project_id,
            experiment_ids=payload.experiment_ids,
        )
        return LastLoggedExperimentsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)
