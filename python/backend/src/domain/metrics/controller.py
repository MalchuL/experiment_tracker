"""HTTP routes under ``/metrics``: upsert and fetch metric definitions for experiments."""

from api.routes.service_dependencies import get_metric_service
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

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
    """Map metric access/not-found errors to HTTP responses."""
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


@router.get("/by-key", response_model=MetricDTO)
async def get_metric_by_key(
    experiment_id: UUID = Query(..., alias="experimentId"),
    name: str = Query(..., min_length=1),
    label: str | None = Query(default=None),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_metric_by_key(
            user,
            experiment_id,
            name,
            label,
        )
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
