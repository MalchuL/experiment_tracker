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
    """Map metric access/not-found errors to HTTP responses.

    Args:
        error: Exception raised by ``MetricService``.

    Raises:
        HTTPException: ``403`` for project metric access failures, ``404`` for missing
            metrics or experiments, and ``400`` for other metric errors.
    """
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
    """Create or update a metric definition/value for an experiment.

    Args:
        data: Metric key, optional label, value, and experiment id from the request body.
        user: Authenticated user performing the write.
        _: API-token scope guard accepting metric create or edit permission.
        metric_service: Metric application service dependency.

    Returns:
        MetricDTO: Created metric or updated existing metric for the same
        experiment/name/label key.

    Raises:
        HTTPException: ``403`` when the project is inaccessible, ``404`` when the
            experiment cannot be found, and ``400`` for validation or repository
            failures.
    """
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
    """Fetch one metric by experiment/name/label key.

    Args:
        experiment_id: Experiment identifier supplied as ``experimentId``.
        name: Metric name within the experiment.
        label: Optional metric label; empty string is treated as an unlabeled metric.
        user: Authenticated user requesting the metric.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric application service dependency.

    Returns:
        MetricDTO: Matching metric definition/value.

    Raises:
        HTTPException: ``403`` for insufficient project metric access, ``404`` for
            missing experiment or metric, and ``400`` for other service errors.
    """
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
    """Delete a metric by id.

    Args:
        metric_id: Metric identifier to remove.
        user: Authenticated user deleting the metric.
        _: API-token scope guard requiring metric delete access.
        metric_service: Metric application service dependency.

    Returns:
        None: FastAPI sends HTTP ``204`` on success.

    Raises:
        HTTPException: ``403`` for insufficient delete permission, ``404`` for
            missing metric or experiment, and ``400`` for other service errors.
    """
    try:
        await metric_service.delete_metric(user, metric_id)
    except Exception as exc:  # noqa: BLE001
        _raise_metric_http_error(exc)
