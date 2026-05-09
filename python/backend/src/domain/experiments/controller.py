"""HTTP routes under ``/experiments``: CRUD, metrics proxy, usage, scoped cleanup, and delete.

Maps domain errors to status codes via ``_raise_experiment_http_error``. Satellite work
(object storage, scalars) is orchestrated in ``ExperimentService``.
"""

from uuid import UUID

from api.routes.service_dependencies import get_experiment_service, get_metric_service
from domain.metrics.dto import MetricListResponseDTO
from domain.metrics.service import MetricService
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User

from lib.category_cleanup_dto import CategoryCleanupResponseDTO
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentDeleteResponseDTO,
    ExperimentListResponseDTO,
    ExperimentReorderDTO,
    ExperimentUpdateDTO,
    ExperimentUsageDTO,
)
from .error import ExperimentNamePatternNotSetError, ExperimentNotAccessibleError
from .service import ExperimentCleanupCategory, ExperimentService
from domain.rbac.permissions import ProjectActions

from lib.logger import get_logger

router = APIRouter(prefix="/experiments", tags=["experiments"])

logger = get_logger(__name__)


def _raise_experiment_http_error(error: Exception) -> None:
    """Translate experiment domain errors into ``HTTPException`` responses."""
    if isinstance(error, ExperimentNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ExperimentNamePatternNotSetError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/recent", response_model=ExperimentListResponseDTO)
async def get_recent_experiments(
    limit: int = Query(default=10, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    project_id: UUID = Query(
        ..., alias="projectId", description="The ID of the project"
    ),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.get_recent_experiments(
            user,
            project_id,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.get("/{experiment_id}/metrics", response_model=MetricListResponseDTO)
async def get_experiment_metrics(
    experiment_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_aggregated_metrics_for_experiment(
            user,
            experiment_id,
            ListOptions(limit=limit, offset=offset),
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


@router.get("/{experiment_id}/usage", response_model=ExperimentUsageDTO)
async def get_experiment_usage(
    experiment_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """Approximate bytes/rows per storage category for UI (danger zone, billing hints).

    Pulls object-storage and scalars satellites in parallel (best-effort); requires view
    access to the experiment's project.
    """
    try:
        return await experiment_service.get_experiment_usage(user, experiment_id)
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.post("/{experiment_id}/cleanup/{category}", response_model=CategoryCleanupResponseDTO)
async def cleanup_experiment_category(
    experiment_id: UUID,
    category: ExperimentCleanupCategory,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """Remove a single storage slice without deleting the experiment row.

    Valid ``category`` values: ``experimentArtifacts``, ``atStepArtifacts``, ``scalars``.
    Project snapshots are not cleaned here — use project-level cleanup for snapshots.

    See ``ExperimentService.cleanup_experiment_category`` for semantics.
    """
    try:
        return await experiment_service.cleanup_experiment_category(
            user, experiment_id, category
        )
    except Exception as exc:  # noqa: BLE001
        _raise_experiment_http_error(exc)


@router.delete("/{experiment_id}", response_model=ExperimentDeleteResponseDTO)
async def delete_experiment(
    experiment_id: UUID,
    detailed: bool = Query(
        False,
        description=(
            "When true, include full per-step ``results`` payloads. "
            "When false (default), ``results`` is empty and ``resultCount`` counts successes."
        ),
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """Hard-delete experiment: satellites first (best-effort), then Postgres row.

    Response includes structured status for object storage and scalars so clients can
    surface partial failures (e.g. storage down) even when the DB delete succeeded.
    """
    try:
        return await experiment_service.delete_experiment(
            user, experiment_id, detailed=detailed
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error deleting experiment: %s", exc, stack_info=True)
        _raise_experiment_http_error(exc)


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
