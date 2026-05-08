"""HTTP routes under ``/projects``: projects, nested experiments/metrics/hypotheses, settings, members.

Errors are normalized with ``_raise_project_http_error`` / ``_raise_project_members_http_error``.
"""

from typing import Any, Dict, List
from uuid import UUID

from domain.hypotheses.dto import HypothesisListResponseDTO
from domain.experiments.dto import (
    ExperimentBatchLookupDTO,
    ExperimentListResponseDTO,
)
from domain.experiments.service import ExperimentService
from domain.hypotheses.service import HypothesisService
from domain.metrics.dto import (
    MetricLabelsResponseDTO,
    MetricListResponseDTO,
    MetricsByLabelSnapshotResponseDTO,
    UniqueMetricDimensionsResponseDTO,
)
from domain.metrics.service import MetricService
from domain.metrics.error import MetricNotAccessibleError, MetricNotFoundError

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from lib.category_cleanup_dto import CategoryCleanupResponseDTO
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User
from domain.rbac.permissions import ProjectActions
from domain.rbac.permissions.team import TeamActions

from .dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectDeleteResponseDTO,
    ProjectListResponseDTO,
    ProjectSettingDTO,
    ProjectUsageDTO,
    ProjectSettingValueUpdateDTO,
    ProjectUpdateDTO,
)
from domain.experiments.error import ExperimentNotAccessibleError

from .errors import ProjectNotAccessibleError, ProjectPermissionError
from .service import ProjectCleanupCategory, ProjectService
from api.routes.service_dependencies import (
    get_experiment_service,
    get_metric_service,
    get_project_members_service,
    get_project_service,
)
from api.routes.service_dependencies import get_hypothesis_service
from domain.projects.members.dto import (
    ProjectMemberInviteDTO,
    ProjectMemberRemoveDTO,
    ProjectMemberRowDTO,
    ProjectMemberUpdateRoleDTO,
    UserLookupDTO,
)
from domain.projects.members.errors import (
    ProjectMemberAccessDenied,
    ProjectMemberInvalidRole,
    ProjectMemberLastEditor,
    ProjectMemberNotFound,
)
from domain.projects.members.service import ProjectMembersService

from lib.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


def _raise_project_http_error(error: Exception) -> None:
    """Map project/metric/scalars-related exceptions to HTTP status codes."""
    if isinstance(error, ExperimentNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, MetricNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, MetricNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ProjectPermissionError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ProjectNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code, detail=error.response.text
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Scalars service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


def _raise_project_members_http_error(error: Exception) -> None:
    """Map project membership invite/update/remove errors to HTTP responses."""
    if isinstance(error, ProjectMemberAccessDenied):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, (ProjectMemberNotFound, ProjectNotAccessibleError)):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ProjectMemberInvalidRole):
        raise HTTPException(status_code=400, detail=str(error))
    if isinstance(error, ProjectMemberLastEditor):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("", response_model=ProjectListResponseDTO)
async def get_all_projects(
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await project_service.get_accessible_projects(
            user,
            list_options=ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/experiments", response_model=ExperimentListResponseDTO)
async def get_project_experiments(
    project_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.get_experiments_by_project(
            user,
            project_id,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.post(
    "/{project_id}/experiments/batch",
    response_model=ExperimentListResponseDTO,
)
async def post_project_experiments_batch(
    project_id: UUID,
    body: ExperimentBatchLookupDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """Load specific experiments by id in one request (same shape as GET …/experiments)."""
    try:
        return await experiment_service.get_experiments_batch_for_project(
            user,
            project_id,
            list(body.experiment_ids),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/hypotheses", response_model=HypothesisListResponseDTO)
async def get_project_hypotheses(
    project_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    try:
        return await hypothesis_service.get_hypotheses_by_project(
            user,
            project_id,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/metric-labels",
    response_model=MetricLabelsResponseDTO,
)
async def get_project_metric_labels(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_metric_labels_for_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/metrics/unique-dimensions",
    response_model=UniqueMetricDimensionsResponseDTO,
)
async def get_project_unique_metric_dimensions(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_unique_metric_dimensions_for_project(
            user, project_id
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/metrics/by-label",
    response_model=MetricsByLabelSnapshotResponseDTO,
)
async def get_project_metrics_by_label(
    project_id: UUID,
    label: str = Query(
        ...,
        description="Metric label filter. Use empty string for unlabeled (NULL) metrics.",
    ),
    include_experiments_without_metrics: bool = Query(
        default=False,
        description="If true, include experiments with no row for this label (cells null).",
    ),
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    try:
        return await metric_service.get_metrics_by_label_snapshot(
            user,
            project_id,
            label,
            include_experiments_without_metrics,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/metrics",
    response_model=MetricListResponseDTO,
)
async def get_aggregatedproject_metrics(
    project_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await metric_service.get_aggregated_metrics_for_project(
            user,
            project_id,
            project_service,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/members", response_model=list[ProjectMemberRowDTO])
async def list_project_members(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    members_service: ProjectMembersService = Depends(get_project_members_service),
):
    try:
        return await members_service.list_members(user.id, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_members_http_error(exc)


@router.get("/{project_id}/users/lookup", response_model=UserLookupDTO)
async def lookup_project_user_by_email(
    project_id: UUID,
    email: str = Query(..., min_length=1, max_length=320),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    members_service: ProjectMembersService = Depends(get_project_members_service),
):
    try:
        return await members_service.lookup_user_by_email(user.id, project_id, email)
    except Exception as exc:  # noqa: BLE001
        _raise_project_members_http_error(exc)


@router.post("/{project_id}/members", response_model=ProjectMemberRowDTO)
async def invite_project_member(
    project_id: UUID,
    data: ProjectMemberInviteDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    members_service: ProjectMembersService = Depends(get_project_members_service),
):
    try:
        return await members_service.invite_member(user.id, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_members_http_error(exc)


@router.patch("/{project_id}/members", response_model=ProjectMemberRowDTO)
async def update_project_member_role(
    project_id: UUID,
    data: ProjectMemberUpdateRoleDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    members_service: ProjectMembersService = Depends(get_project_members_service),
):
    try:
        return await members_service.update_member_role(user.id, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_members_http_error(exc)


@router.delete("/{project_id}/members")
async def remove_project_member(
    project_id: UUID,
    data: ProjectMemberRemoveDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    members_service: ProjectMembersService = Depends(get_project_members_service),
):
    try:
        await members_service.remove_member(user.id, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_members_http_error(exc)
    return {"success": True}


@router.get("/{project_id}", response_model=ProjectDTO)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        project = await project_service.get_project_if_accessible(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectDTO)
async def create_project(
    data: ProjectCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(TeamActions.CREATE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await project_service.create_project(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.patch("/{project_id}", response_model=ProjectDTO)
async def update_project(
    project_id: UUID,
    data: ProjectUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await project_service.update_project(user, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/usage", response_model=ProjectUsageDTO)
async def get_project_usage(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Project-wide storage breakdown: CAS artifacts, snapshots, experiment buckets, scalars.

    Used by the project settings danger zone; combines object-storage and ClickHouse usage.
    """
    try:
        return await project_service.get_project_usage(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.post("/{project_id}/cleanup/{category}", response_model=CategoryCleanupResponseDTO)
async def cleanup_project_category(
    project_id: UUID,
    category: ProjectCleanupCategory,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Danger-zone partial wipe: one of project artifacts, snapshots, buckets, or full scalars tables.

    Requires project delete permission; does **not** remove the Postgres project record.
    """
    try:
        return await project_service.cleanup_project_category(
            user, project_id, category
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error creating project: %s", exc, stack_info=True)
        _raise_project_http_error(exc)


@router.post("/{project_id}/settings", response_model=List[ProjectSettingDTO])
async def add_project_settings(
    project_id: UUID,
    data: ProjectSettingDTO | List[ProjectSettingDTO],
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Add one or multiple project setting entries.

    Purpose:
        Creates plugin/SDK settings in the project's dynamic settings list.

    Response:
        List[ProjectSettingDTO]: the full, updated settings list after insertion.
    """
    entries = data if isinstance(data, list) else [data]
    try:
        return await project_service.add_project_settings(user, project_id, entries)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/settings", response_model=List[ProjectSettingDTO])
async def get_project_settings(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch project settings as full structured entries.

    Purpose:
        Returns settings editor-friendly data with metadata and typed values.

    Response:
        List[ProjectSettingDTO]: each item contains `name`, `description`, `type`, `value`.
    """
    try:
        return await project_service.get_project_settings(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/settings/map", response_model=Dict[str, Any])
async def get_project_settings_map(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Fetch project settings as a name-to-value map.

    Purpose:
        Provides compact settings for consumers that only need runtime values.

    Response:
        Dict[str, Any]: `{setting_name: setting_value}`.
    """
    try:
        return await project_service.get_project_settings_map(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.patch("/{project_id}/settings/{name}", response_model=ProjectSettingDTO)
async def update_project_setting_value(
    project_id: UUID,
    name: str,
    data: ProjectSettingValueUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Update one setting value by key with backend type validation.

    Purpose:
        Changes only the `value` field for an existing setting while enforcing
        the setting's declared type.

    Response:
        ProjectSettingDTO: the updated setting entry.
    """
    try:
        return await project_service.update_project_setting_value(
            user, project_id, name, data.value
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.delete("/{project_id}/settings/{name}", response_model=Dict[str, bool])
async def delete_project_setting(
    project_id: UUID,
    name: str,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Delete a project setting by key.

    Purpose:
        Removes one dynamic setting entry from the project's settings list.

    Response:
        Dict[str, bool]: `{\"success\": true}` when deletion succeeds.
    """
    try:
        success = await project_service.delete_project_setting(user, project_id, name)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error deleting project setting: %s", exc, stack_info=True)
        _raise_project_http_error(exc)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Project setting '{name}' not found"
        )
    return {"success": True}


@router.delete("/{project_id}", response_model=ProjectDeleteResponseDTO)
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await project_service.delete_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error deleting project: %s", exc, stack_info=True)
        _raise_project_http_error(exc)
