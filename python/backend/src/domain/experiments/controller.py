from typing import List
from uuid import UUID

from api.routes.service_dependencies import get_experiment_service, get_metric_service
from domain.metrics.dto import MetricDTO
from domain.metrics.service import MetricService
from fastapi import APIRouter, Depends, HTTPException

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from models import User

from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentReorderDTO,
    ExperimentUpdateDTO,
)
from .error import ExperimentNamePatternNotSetError, ExperimentNotAccessibleError
from .service import ExperimentService
from domain.rbac.permissions import ProjectActions

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _raise_experiment_http_error(error: Exception) -> None:
    if isinstance(error, ExperimentNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ExperimentNamePatternNotSetError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/recent", response_model=List[ExperimentDTO])
async def get_recent_experiments(
    limit: int = 10,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.get_recent_experiments(user, limit)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.get("/{experiment_id}/metrics", response_model=List[MetricDTO])
async def get_experiment_metrics(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_aggregated_metrics_for_experiment(
            user, experiment_id
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.get("/{experiment_id}", response_model=ExperimentDTO)
async def get_experiment(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.get_experiment_if_accessible(
            user, experiment_id
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.post("", response_model=ExperimentDTO)
async def create_experiment(
    data: ExperimentCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.create_experiment(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.patch("/{experiment_id}", response_model=ExperimentDTO)
async def update_experiment(
    experiment_id: UUID,
    data: ExperimentUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.update_experiment(user, experiment_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        success = await experiment_service.delete_experiment(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"success": True}


@router.post("/reorder")
async def reorder_experiments(
    data: ExperimentReorderDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        await experiment_service.reorder_experiments(
            user, data.project_id, data.experiment_ids
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)
    return {"success": True}
