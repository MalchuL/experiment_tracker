from typing import Dict, List
from uuid import UUID

from domain.hypotheses.dto import HypothesisDTO
from domain.experiments.dto import ExperimentDTO
from domain.experiments.service import ExperimentService
from domain.hypotheses.service import HypothesisService
from domain.metrics.dto import MetricDTO as MetricDTO
from domain.metrics.service import MetricService
from lib.types import UUID_TYPE
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from db.database import get_async_session
from models import User
from domain.rbac.permissions import ProjectActions
from domain.rbac.permissions.team import TeamActions

from .dto import ProjectCreateDTO, ProjectDTO, ProjectUpdateDTO
from .errors import ProjectNotAccessibleError, ProjectPermissionError
from .service import ProjectService

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
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(session)
    try:
        return await service.get_accessible_projects(user)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/experiments", response_model=List[ExperimentDTO])
async def get_project_experiments(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_EXPERIMENT)),
    session: AsyncSession = Depends(get_async_session),
):
    service = ExperimentService(session)
    try:
        return await service.get_experiments_by_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}/hypotheses", response_model=List[HypothesisDTO])
async def get_project_hypotheses(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    session: AsyncSession = Depends(get_async_session),
):
    service = HypothesisService(session)
    try:
        return await service.get_hypotheses_by_project(user, project_id)
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
    session: AsyncSession = Depends(get_async_session),
):
    service = MetricService(session)
    try:
        return await service.get_aggregated_metrics_for_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.get("/{project_id}", response_model=ProjectDTO)
async def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_PROJECT)),
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(session)
    try:
        project = await service.get_project_if_accessible(user, project_id)
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
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(session)
    try:
        return await service.create_project(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.patch("/{project_id}", response_model=ProjectDTO)
async def update_project(
    project_id: UUID,
    data: ProjectUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_PROJECT)),
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(session)
    try:
        return await service.update_project(user, project_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_PROJECT)),
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectService(session)
    try:
        success = await service.delete_project(user, project_id)
    except Exception as exc:  # noqa: BLE001
        _raise_project_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}
