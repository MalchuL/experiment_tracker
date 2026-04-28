from api.routes.service_dependencies import get_metric_service
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.routes.auth import (
    get_current_user_dual,
    require_api_token_scopes,
    require_api_token_scopes_any,
)
from models import User
from domain.rbac.permissions import ProjectActions

from .dto import MetricDTO, MetricUpsertDTO
from .error import MetricNotAccessibleError, MetricNotFoundError
from .service import MetricService

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _raise_metric_http_error(error: Exception) -> None:
    if isinstance(error, MetricNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, MetricNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=MetricDTO)
async def upsert_metric(
    data: MetricUpsertDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes_any(
            [ProjectActions.CREATE_METRIC, ProjectActions.EDIT_METRIC]
        )
    ),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.upsert_metric(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_metric_http_error(exc)


@router.delete("/{metric_id}", status_code=204)
async def delete_metric(
    metric_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        await metric_service.delete_metric(user, metric_id)
    except Exception as exc:  # noqa: BLE001
        _raise_metric_http_error(exc)
