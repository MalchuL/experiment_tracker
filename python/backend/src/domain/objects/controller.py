from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_objects_service
from domain.rbac.permissions import ProjectActions
from models import User

from .dto import (
    LogObjectRequestDTO,
    LogObjectResponseDTO,
    LogObjectsRequestDTO,
    LogObjectsResponseDTO,
    ObjectsResultDTO,
)
from .error import ObjectsNotAccessibleError
from .service import ObjectsServiceProtocol

router = APIRouter(prefix="/objects", tags=["objects"])


def _raise_objects_http_error(error: Exception) -> None:
    if isinstance(error, ObjectsNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        detail = error.response.text
        raise HTTPException(status_code=status, detail=detail)
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Objects service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


@router.post("/log/{experiment_id}", response_model=LogObjectResponseDTO)
async def log_object(
    experiment_id: UUID,
    data: LogObjectRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    objects_service: ObjectsServiceProtocol = Depends(get_objects_service),
):
    try:
        result = await objects_service.log_object(user, experiment_id, data.model_dump())
        return LogObjectResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_objects_http_error(exc)


@router.post("/log_batch/{experiment_id}", response_model=LogObjectsResponseDTO)
async def log_objects_batch(
    experiment_id: UUID,
    data: LogObjectsRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_METRIC)),
    objects_service: ObjectsServiceProtocol = Depends(get_objects_service),
):
    try:
        result = await objects_service.log_objects_batch(
            user, experiment_id, data.model_dump()
        )
        return LogObjectsResponseDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_objects_http_error(exc)


@router.get("/get/project/{project_id}", response_model=ObjectsResultDTO)
async def get_project_objects(
    project_id: UUID,
    experiment_id: list[UUID] | None = Query(default=None),
    object_type: list[str] | None = Query(default=None),
    name: list[str] | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    objects_service: ObjectsServiceProtocol = Depends(get_objects_service),
):
    try:
        result = await objects_service.get_objects(
            user=user,
            project_id=project_id,
            experiment_ids=experiment_id,
            object_types=object_type,
            names=name,
            start_time=start_time,
            end_time=end_time,
        )
        return ObjectsResultDTO.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        _raise_objects_http_error(exc)
