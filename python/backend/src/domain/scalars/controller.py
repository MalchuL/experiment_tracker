from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from domain.rbac.permissions import ProjectActions
from domain.rbac.wrapper import PermissionChecker
from models import User

from .dto import (
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    LogScalarsRequestDTO,
    LogScalarsResponseDTO,
    ScalarsPointsResultDTO,
)
from .service import ScalarsServiceProtocol
from api.routes.service_dependencies import get_scalars_service

router = APIRouter(prefix="/scalars", tags=["scalars"])


def _raise_scalars_http_error(error: Exception) -> None:
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
        result = await scalars_service.log_scalar(
            user, str(experiment_id), data.model_dump()
        )
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
            user, str(experiment_id), data.model_dump()
        )
        return LogScalarsResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/{experiment_id}", response_model=ScalarsPointsResultDTO)
async def get_scalars(
    experiment_id: UUID,
    max_points: int | None = Query(default=None, ge=1),
    return_tags: bool = Query(default=False),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    scalars_service: ScalarsServiceProtocol = Depends(get_scalars_service),
):
    try:
        result = await scalars_service.get_scalars(
            user,
            str(experiment_id),
            max_points=max_points,
            return_tags=return_tags,
        )
        return ScalarsPointsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)
