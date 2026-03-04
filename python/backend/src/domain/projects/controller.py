from typing import Any, Dict, List
from uuid import UUID

from domain.hypotheses.dto import HypothesisDTO
from domain.experiments.dto import ExperimentDTO
from domain.experiments.service import ExperimentService
from domain.hypotheses.service import HypothesisService
from domain.metrics.dto import MetricDTO as MetricDTO
from domain.metrics.service import MetricService

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from models import User
from domain.rbac.permissions import ProjectActions
from domain.rbac.permissions.team import TeamActions

from .dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectSettingDTO,
    ProjectSettingValueUpdateDTO,
    ProjectUpdateDTO,
)
from .errors import ProjectNotAccessibleError, ProjectPermissionError
from .service import ProjectService
from api.routes.service_dependencies import (
    get_experiment_service,
    get_project_service,
    get_metric_service,
)
from api.routes.service_dependencies import get_hypothesis_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _raise_project_http_error(error: Exception) -> None:
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


@router.get("", response_model=List[ProjectDTO])
async def get_all_projects(
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await project_service.get_accessible_projects(user)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/experiments", response_model=List[ExperimentDTO])
async def get_project_experiments(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    experiment_service: ExperimentService = Depends(get_experiment_service),
):
    try:
        return await experiment_service.get_experiments_by_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/hypotheses", response_model=List[HypothesisDTO])
async def get_project_hypotheses(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    try:
        return await hypothesis_service.get_hypotheses_by_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get(
    "/{project_id}/metrics",
    response_model=List[MetricDTO],
)
async def get_aggregatedproject_metrics(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_METRIC)),
    metric_service: MetricService = Depends(get_metric_service),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return await metric_service.get_aggregated_metrics_for_project(
            user, project_id, project_service
        )
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


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
        _raise_project_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project setting '{name}' not found")
    return {"success": True}


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        success = await project_service.delete_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}
