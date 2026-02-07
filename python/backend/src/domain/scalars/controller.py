from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from config.settings import get_settings
from db.database import get_async_session
from domain.rbac.permissions import ProjectActions
from domain.rbac.wrapper import PermissionChecker
from models import User

from .client import ScalarsServiceClient
from .dto import (
    LogScalarRequestDTO,
    LogScalarResponseDTO,
    LogScalarsRequestDTO,
    LogScalarsResponseDTO,
    ScalarsPointsResultDTO,
)

router = APIRouter(prefix="/scalars", tags=["scalars"])


def _raise_scalars_http_error(error: Exception) -> None:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        detail = error.response.text
        raise HTTPException(status_code=status, detail=detail)
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Scalars service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


async def _ensure_can_create_metric(
    user: User, project_id: UUID, session: AsyncSession
) -> None:
    checker = PermissionChecker(session)
    if not await checker.can_create_metric(user.id, project_id):
        raise HTTPException(status_code=403, detail="Project access denied")


async def _ensure_can_view_metric(
    user: User, project_id: UUID, session: AsyncSession
) -> None:
    checker = PermissionChecker(session)
    if not await checker.can_view_metric(user.id, project_id):
        raise HTTPException(status_code=403, detail="Project access denied")


@router.post("/log/{project_id}/{experiment_id}", response_model=LogScalarResponseDTO)
async def log_scalar(
    project_id: UUID,
    experiment_id: UUID,
    data: LogScalarRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    session: AsyncSession = Depends(get_async_session),
):
    await _ensure_can_create_metric(user, project_id, session)
    client = ScalarsServiceClient(get_settings().scalars_service_url)
    try:
        result = await client.log_scalar(
            str(project_id), str(experiment_id), data.model_dump()
        )
        return LogScalarResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.post(
    "/log_batch/{project_id}/{experiment_id}",
    response_model=LogScalarsResponseDTO,
)
async def log_scalars_batch(
    project_id: UUID,
    experiment_id: UUID,
    data: LogScalarsRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    session: AsyncSession = Depends(get_async_session),
):
    await _ensure_can_create_metric(user, project_id, session)
    client = ScalarsServiceClient(get_settings().scalars_service_url)
    try:
        result = await client.log_scalars_batch(
            str(project_id), str(experiment_id), data.model_dump()
        )
        return LogScalarsResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)


@router.get("/get/{project_id}", response_model=ScalarsPointsResultDTO)
async def get_scalars(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    max_points: int | None = Query(default=None, ge=1),
    return_tags: bool = Query(default=False),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    session: AsyncSession = Depends(get_async_session),
):
    await _ensure_can_view_metric(user, project_id, session)
    client = ScalarsServiceClient(get_settings().scalars_service_url)
    try:
        result = await client.get_scalars(
            str(project_id),
            experiment_ids=[str(eid) for eid in experiment_id] if experiment_id else None,
            max_points=max_points,
            return_tags=return_tags,
        )
        return ScalarsPointsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_scalars_http_error(exc)
