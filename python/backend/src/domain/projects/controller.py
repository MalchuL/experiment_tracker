"""HTTP routes under ``/projects``: projects, nested experiments/metrics/hypotheses, settings, members.

Errors are normalized with ``_raise_project_http_error`` / ``_raise_project_members_http_error``.
"""

from typing import Any, Dict, List
from uuid import UUID

from domain.hypotheses.dto import HypothesisListResponseDTO
from domain.project_reports.dto import ProjectReportListResponseDTO
from domain.experiments.dto import (
    ExperimentBatchLookupDTO,
    ExperimentListResponseDTO,
)
from domain.experiments.service import ExperimentService
from domain.experiment_data.dto import (
    ExperimentHparamsListRequestDTO,
    ExperimentHparamsListResponseDTO,
)
from domain.experiment_data.error import ExperimentDataNotAccessibleError
from domain.experiment_data.service import ExperimentDataService
from domain.hypotheses.service import HypothesisService
from domain.project_reports.service import ProjectReportService
from domain.metrics.dto import (
    MetricLabelsResponseDTO,
    MetricListResponseDTO,
    MetricsByLabelSnapshotResponseDTO,
    SelectiveMetricsBatchRequestDTO,
    SelectiveTopMetricsRequestDTO,
    TopMetricsResponseDTO,
    UniqueMetricDimensionsResponseDTO,
)
from domain.metrics.service import MetricService
from domain.metrics.error import MetricNotAccessibleError, MetricNotFoundError

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
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
    ProjectOwnerTransferDTO,
    ProjectTeamTransferDTO,
    ProjectUpdateDTO,
)
from domain.experiments.error import ExperimentNotAccessibleError

from .errors import ProjectNotAccessibleError, ProjectPermissionError, ProjectTransferError
from .service import ProjectCleanupCategory, ProjectService
from api.routes.service_dependencies import (
    get_experiment_service,
    get_experiment_data_service,
    get_hypothesis_service,
    get_metric_service,
    get_project_members_service,
    get_project_report_service,
    get_project_service,
)
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
    """Map project/metric/scalars-related exceptions to HTTP status codes.

    Args:
        error: Exception raised by project, experiment, metric, report, or satellite
            service calls.

    Raises:
        HTTPException: ``403`` for permission failures, ``404`` for inaccessible or
            missing resources, upstream status codes for satellite HTTP errors,
            ``502`` for satellite connectivity errors, and ``400`` otherwise.
    """
    if isinstance(error, (ExperimentNotAccessibleError, ExperimentDataNotAccessibleError)):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, MetricNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, MetricNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ProjectPermissionError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ProjectTransferError):
        raise HTTPException(status_code=400, detail=str(error))
    if isinstance(error, ProjectNotAccessibleError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=error.response.status_code, detail=error.response.text
        )
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="Scalars service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


@router.post(
    "/{project_id}/experiments/hparams/list",
    response_model=ExperimentHparamsListResponseDTO,
)
async def list_project_experiment_hparams(
    project_id: UUID,
    body: ExperimentHparamsListRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    service: ExperimentDataService = Depends(get_experiment_data_service),
) -> ExperimentHparamsListResponseDTO:
    try:
        return await service.list_hparams(user, project_id, list(body.experiment_ids))
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


def _raise_project_members_http_error(error: Exception) -> None:
    """Map project membership invite/update/remove errors to HTTP responses.

    Args:
        error: Exception raised by ``ProjectMembersService``.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing members/projects,
            and ``400`` for invalid roles, last-editor protection, or other errors.
    """
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
    """List projects accessible to the current user.

    Args:
        limit: Maximum number of projects to return.
        offset: Number of projects to skip.
        user: Authenticated user requesting projects.
        _: API-token scope guard requiring project view access.
        project_service: Project application service dependency.

    Returns:
        ProjectListResponseDTO: Paginated project list with counts.

    Raises:
        HTTPException: ``403``, ``404``, ``502``, or ``400`` via project error mapping.
    """
    try:
        return await project_service.get_accessible_projects(
            user,
            list_options=ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/experiments",
    response_model=ExperimentListResponseDTO,
    response_model_exclude_none=True,
)
async def get_project_experiments(
    project_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(
        default=None,
        max_length=200,
        description="Optional case-insensitive substring on experiment id, name, or description.",
    ),
    include_features: bool = Query(
        default=True,
        alias="includeFeatures",
        description="When true, include experiment feature trees in each list item.",
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """List experiments for a project.

    Args:
        project_id: Project identifier.
        limit: Maximum number of experiments to return.
        offset: Number of experiments to skip.
        search: Optional substring filter.
        include_features: Whether feature trees should be included.
        user: Authenticated user requesting experiments.
        _: API-token scope guard requiring experiment view access.
        experiment_service: Experiment service dependency.

    Returns:
        ExperimentListResponseDTO: Paginated experiment list items.

    Raises:
        HTTPException: ``404`` for inaccessible projects/experiments or ``400`` for
            other service errors.
    """
    try:
        return await experiment_service.get_experiments_by_project(
            user,
            project_id,
            ListOptions(limit=limit, offset=offset),
            search=search,
            include_features=include_features,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "get_project_experiments failed project_id=%s limit=%s offset=%s search=%r",
            project_id,
            limit,
            offset,
            search,
        )
        _raise_project_http_error(exc)


@router.post(
    "/{project_id}/experiments/batch",
    response_model=ExperimentListResponseDTO,
    response_model_exclude_none=True,
)
async def post_project_experiments_batch(
    project_id: UUID,
    body: ExperimentBatchLookupDTO,
    include_features: bool = Query(
        default=True,
        alias="includeFeatures",
        description="When true, include experiment feature trees in each list item.",
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    """Load specific experiments by id in one request.

    Args:
        project_id: Project that must own returned experiments.
        body: Requested experiment ids.
        include_features: Whether feature trees should be included.
        user: Authenticated user requesting experiments.
        _: API-token scope guard requiring experiment view access.
        experiment_service: Experiment service dependency.

    Returns:
        ExperimentListResponseDTO: Matching experiments in request order.

    Raises:
        HTTPException: ``404`` for inaccessible projects or ``400`` for service errors.
    """
    try:
        return await experiment_service.get_experiments_batch_for_project(
            user,
            project_id,
            list(body.experiment_ids),
            include_features=include_features,
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
    """List hypotheses for a project.

    Args:
        project_id: Project identifier.
        limit: Maximum number of hypotheses to return.
        offset: Number of hypotheses to skip.
        user: Authenticated user requesting hypotheses.
        _: API-token scope guard requiring hypothesis view access.
        hypothesis_service: Hypothesis service dependency.

    Returns:
        HypothesisListResponseDTO: Paginated hypothesis list.

    Raises:
        HTTPException: Project error mapping for access and service failures.
    """
    try:
        return await hypothesis_service.get_hypotheses_by_project(
            user,
            project_id,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/reports", response_model=ProjectReportListResponseDTO)
async def get_project_reports(
    project_id: UUID,
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_REPORT)),
    report_service: ProjectReportService = Depends(get_project_report_service),
):
    """List reports for a project.

    Args:
        project_id: Project identifier.
        limit: Maximum number of reports to return.
        offset: Number of reports to skip.
        user: Authenticated user requesting reports.
        _: API-token scope guard requiring report view access.
        report_service: Project report service dependency.

    Returns:
        ProjectReportListResponseDTO: Paginated report summaries.

    Raises:
        HTTPException: Project error mapping for access and service failures.
    """
    try:
        return await report_service.get_reports_by_project(
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
    """Return distinct metric labels for a project.

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting metric metadata.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service dependency.

    Returns:
        MetricLabelsResponseDTO: Distinct labels and unlabeled-metric flag.

    Raises:
        HTTPException: Project/metric error mapping for access and service failures.
    """
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
    """Return unique metric name/label dimensions for a project.

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting metric metadata.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service dependency.

    Returns:
        UniqueMetricDimensionsResponseDTO: Unique metric dimension pairs.

    Raises:
        HTTPException: Project/metric error mapping for access and service failures.
    """
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
    """Return a latest-value metric snapshot for one label.

    Args:
        project_id: Project identifier.
        label: Metric label filter; empty string means unlabeled metrics.
        include_experiments_without_metrics: Whether to include null-valued rows.
        limit: Maximum number of experiment rows to return.
        offset: Number of experiment rows to skip.
        user: Authenticated user requesting the snapshot.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service dependency.

    Returns:
        MetricsByLabelSnapshotResponseDTO: Table columns and experiment rows.

    Raises:
        HTTPException: Project/metric error mapping for access and service failures.
    """
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
    """Return configured aggregate metrics for a project.

    Args:
        project_id: Project identifier.
        limit: Maximum number of aggregate rows to return.
        offset: Number of aggregate rows to skip.
        user: Authenticated user requesting metrics.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service dependency.
        project_service: Project service dependency used for metric configuration.

    Returns:
        MetricListResponseDTO: Paginated aggregate metric rows.

    Raises:
        HTTPException: Project/metric error mapping for access, unsupported
            aggregation, and service failures.
    """
    try:
        return await metric_service.get_aggregated_metrics_for_project(
            user,
            project_id,
            project_service,
            ListOptions(limit=limit, offset=offset),
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.post(
    "/{project_id}/metrics/batch",
    response_model=MetricListResponseDTO,
)
async def post_selective_project_metrics_batch(
    project_id: UUID,
    body: SelectiveMetricsBatchRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    """Return selected existing metrics for selected project experiments.

    Purpose:
        Support scroll-paginated clients that need only currently loaded experiment
        rows and visible metric columns, avoiding the legacy project-wide response.

    Args:
        project_id: Project that must own all returned metrics.
        body: Bounded experiment identifiers and exact metric name/label keys.
        user: Authenticated user requesting metrics.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service providing additive selective reads.

    Returns:
        MetricListResponseDTO: Complete non-paginated selective metric response.
        Missing, foreign-project, and duplicate selections are omitted.

    Raises:
        HTTPException: Project/metric error mapping for access and service failures.
    """
    try:
        return await metric_service.get_selective_metrics_for_project(
            user,
            project_id,
            body.metrics,
            body.experiment_ids,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.post(
    "/{project_id}/metrics/top",
    response_model=TopMetricsResponseDTO,
)
async def post_selective_project_top_metrics(
    project_id: UUID,
    body: SelectiveTopMetricsRequestDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
):
    """Return project-wide top positions for selected existing metric keys.

    Purpose:
        Let clients request ranking data only for visible metrics while retaining
        project-wide ranks. Each requested metric explicitly supplies its direction.

    Args:
        project_id: Project whose experiments form the ranking population.
        body: Exact metric keys and highest competition-ranking position to return.
        user: Authenticated user requesting rankings.
        _: API-token scope guard requiring metric view access.
        metric_service: Metric service providing additive selective rankings.

    Returns:
        TopMetricsResponseDTO: Ranking entries containing metric key, position,
        value, and experiment identifier. Tied values share a position.

    Raises:
        HTTPException: Project/metric error mapping for access and service failures.
    """
    try:
        return await metric_service.get_selective_top_metrics_for_project(
            user,
            project_id,
            body.metrics,
            body.k,
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
    """List effective members for a project.

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting members.
        _: API-token scope guard requiring project view access.
        members_service: Project members service dependency.

    Returns:
        list[ProjectMemberRowDTO]: Direct, inherited, and override member rows.

    Raises:
        HTTPException: Project-member error mapping for access and service failures.
    """
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
    """Look up an active user by email for project membership.

    Args:
        project_id: Project identifier.
        email: Email address to search.
        user: Authenticated user performing the lookup.
        _: API-token scope guard requiring project edit access.
        members_service: Project members service dependency.

    Returns:
        UserLookupDTO: Matching active user's identity.

    Raises:
        HTTPException: Project-member error mapping for access, missing user, or
            service failures.
    """
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
    """Invite an existing user to a project with a role.

    Args:
        project_id: Project identifier.
        data: Invite payload with email and role.
        user: Authenticated user granting access.
        _: API-token scope guard requiring project edit access.
        members_service: Project members service dependency.

    Returns:
        ProjectMemberRowDTO: Effective member row after invite.

    Raises:
        HTTPException: Project-member error mapping for access, invalid roles, missing
            users, and service failures.
    """
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
    """Update a project member role or team-member override.

    Args:
        project_id: Project identifier.
        data: Target user id and replacement role.
        user: Authenticated user changing the role.
        _: API-token scope guard requiring project edit access.
        members_service: Project members service dependency.

    Returns:
        ProjectMemberRowDTO: Effective member row after update.

    Raises:
        HTTPException: Project-member error mapping for access, invalid roles, missing
            members, and service failures.
    """
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
    """Remove direct project permissions for a member.

    Args:
        project_id: Project identifier.
        data: Target user id.
        user: Authenticated user removing access.
        _: API-token scope guard requiring project edit access.
        members_service: Project members service dependency.

    Returns:
        dict[str, bool]: ``{"success": True}`` after removal.

    Raises:
        HTTPException: Project-member error mapping for access, last-editor
            protection, and service failures.
    """
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
    """Return one project visible to the current user.

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting the project.
        _: API-token scope guard requiring project view access.
        project_service: Project service dependency.

    Returns:
        ProjectDTO: Full project metadata and configuration.

    Raises:
        HTTPException: ``404`` for missing/inaccessible projects and mapped service
            errors otherwise.
    """
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
    """Create a project.

    Args:
        data: Project create payload, optionally including a team id.
        user: Authenticated user creating the project.
        _: API-token scope guard requiring team/project creation access.
        project_service: Project service dependency.

    Returns:
        ProjectDTO: Created project with initial counts.

    Raises:
        HTTPException: Project error mapping for permission, satellite, and
            persistence failures.
    """
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
    """Update project metadata and configuration.

    Args:
        project_id: Project identifier.
        data: Project update payload.
        user: Authenticated user editing the project.
        _: API-token scope guard requiring project edit access.
        project_service: Project service dependency.

    Returns:
        ProjectDTO: Updated project.

    Raises:
        HTTPException: Project error mapping for permission and service failures.
    """
    try:
        return await project_service.update_project(user, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.patch("/{project_id}/team", response_model=ProjectDTO)
async def change_project_team(
    project_id: UUID,
    data: ProjectTeamTransferDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes(
            [
                ProjectActions.EDIT_PROJECT,
                TeamActions.CREATE_PROJECT,
                TeamActions.DELETE_PROJECT,
            ]
        )
    ),
    project_service: ProjectService = Depends(get_project_service),
):
    """Move a project to another team or make it standalone.

    Args:
        project_id: Project identifier to transfer.
        data: Destination team and optional owner payload.
        user: Authenticated user requesting the transfer.
        _: API-token scope guard requiring project edit, project create, and
            team-project delete access.
        project_service: Project application service dependency.

    Returns:
        ProjectDTO: Updated project with its resulting team and owner.

    Raises:
        HTTPException: Project error mapping for permissions, invalid transfers, and
            missing resources.
    """
    try:
        return await project_service.change_project_team(user, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.patch("/{project_id}/owner", response_model=ProjectDTO)
async def change_project_owner(
    project_id: UUID,
    data: ProjectOwnerTransferDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Transfer ownership of a standalone project.

    Args:
        project_id: Standalone project identifier.
        data: New owner payload.
        user: Authenticated user requesting the transfer.
        _: API-token scope guard requiring project edit access.
        project_service: Project application service dependency.

    Returns:
        ProjectDTO: Updated project with the new owner.

    Raises:
        HTTPException: Project error mapping for permissions, invalid transfers, and
            missing resources.
    """
    try:
        return await project_service.change_project_owner(user, project_id, data)
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

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting usage.
        _: API-token scope guard requiring project view access.
        project_service: Project service dependency.

    Returns:
        ProjectUsageDTO: Usage blocks and total bytes.

    Raises:
        HTTPException: Project error mapping for access, satellite, and service
            failures.
    """
    try:
        return await project_service.get_project_usage(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.post(
    "/{project_id}/cleanup/{category}", response_model=CategoryCleanupResponseDTO
)
async def cleanup_project_category(
    project_id: UUID,
    category: ProjectCleanupCategory,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Danger-zone partial wipe: one of project artifacts, snapshots, buckets, or full scalars tables.

    Requires project delete permission; does **not** remove the Postgres project record.

    Args:
        project_id: Project identifier.
        category: Storage category to clean.
        user: Authenticated user requesting cleanup.
        _: API-token scope guard requiring project delete access.
        project_service: Project service dependency.

    Returns:
        CategoryCleanupResponseDTO: Structured cleanup results and errors.

    Raises:
        HTTPException: Project error mapping for permission, unknown category, and
            satellite failures.
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

    Args:
        project_id: Project identifier.
        data: Single setting or list of settings to append.
        user: Authenticated user editing settings.
        _: API-token scope guard requiring project edit access.
        project_service: Project service dependency.

    Returns:
        List[ProjectSettingDTO]: the full, updated settings list after insertion.

    Raises:
        HTTPException: Project error mapping for permission, duplicate names, type
            validation, and persistence failures.
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

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting settings.
        _: API-token scope guard requiring project view access.
        project_service: Project service dependency.

    Returns:
        List[ProjectSettingDTO]: each item contains `name`, `description`, `type`, `value`.

    Raises:
        HTTPException: Project error mapping for access and service failures.
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

    Args:
        project_id: Project identifier.
        user: Authenticated user requesting runtime settings.
        _: API-token scope guard requiring project view access.
        project_service: Project service dependency.

    Returns:
        Dict[str, Any]: `{setting_name: setting_value}`.

    Raises:
        HTTPException: Project error mapping for access and service failures.
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

    Args:
        project_id: Project identifier.
        name: Setting name to update.
        data: Payload containing the replacement value.
        user: Authenticated user editing settings.
        _: API-token scope guard requiring project edit access.
        project_service: Project service dependency.

    Returns:
        ProjectSettingDTO: the updated setting entry.

    Raises:
        HTTPException: Project error mapping for permission, missing setting, type
            validation, and persistence failures.
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

    Args:
        project_id: Project identifier.
        name: Setting name to delete.
        user: Authenticated user editing settings.
        _: API-token scope guard requiring project edit access.
        project_service: Project service dependency.

    Returns:
        Dict[str, bool]: `{\"success\": true}` when deletion succeeds.

    Raises:
        HTTPException: Project error mapping for permission, missing setting, and
            persistence failures.
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
    detailed: bool = Query(
        False,
        description=(
            "When true, include full per-step ``results``. "
            "When false (default), ``results`` is empty and ``resultCount`` counts successes."
        ),
    ),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    """Delete a project and clean up satellite data.

    Args:
        project_id: Project identifier to delete.
        detailed: Whether to include full cleanup result payloads.
        user: Authenticated user deleting the project.
        _: API-token scope guard requiring project delete access.
        project_service: Project service dependency.

    Returns:
        ProjectDeleteResponseDTO: Structured cleanup outcome for satellites and the
        Postgres project row.

    Raises:
        HTTPException: Project error mapping for permission, satellite, and repository
            failures.
    """
    try:
        return await project_service.delete_project(user, project_id, detailed=detailed)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error deleting project: %s", exc, stack_info=True)
        _raise_project_http_error(exc)
