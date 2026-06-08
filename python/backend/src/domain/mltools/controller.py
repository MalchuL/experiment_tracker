"""Expose authenticated main-backend routes for MLTools importance jobs.

The controller keeps authorization and public API error semantics in the main
backend while delegating job persistence and execution to the MLTools service.
"""

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from api.routes.service_dependencies import get_mltools_service
from clients.mltools.dto import (
    MLToolsCreateJobDTO,
    MLToolsCreateJobResponseDTO,
    MLToolsJobDTO,
    MLToolsJobListDTO,
    MLToolsMessagesDTO,
    MLToolsResultsDTO,
)
from domain.mltools.service import MLToolsService
from domain.projects.errors import ProjectPermissionError
from domain.rbac.permissions import ProjectActions
from models import User

router = APIRouter(prefix="/projects/{project_id}/mltools/hparams/importance/jobs", tags=["mltools"])


def _raise_mltools_error(error: Exception) -> None:
    """Translate domain and downstream MLTools failures into HTTP responses.

    Args:
        error: Exception raised while authorizing or proxying an MLTools call.

    Returns:
        This function never returns.

    Raises:
        HTTPException: Always, with a status appropriate to the failure type.
    """
    if isinstance(error, ProjectPermissionError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(status_code=error.response.status_code, detail=error.response.text)
    if isinstance(error, httpx.RequestError):
        raise HTTPException(status_code=502, detail="MLTools service unavailable")
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=MLToolsCreateJobResponseDTO)
async def create_mltools_job(
    project_id: UUID,
    body: MLToolsCreateJobDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes(
            [
                ProjectActions.EDIT_EXPERIMENT,
                ProjectActions.VIEW_EXPERIMENT,
                ProjectActions.VIEW_METRIC,
            ]
        )
    ),
    service: MLToolsService = Depends(get_mltools_service),
):
    """Create and enqueue a hyperparameter-importance job.

    Args:
        project_id: Project whose experiments will be analyzed.
        body: Requested target metrics and analysis configuration.
        user: Authenticated user resolved from a session or API token.
        _: Dependency result used solely to enforce API-token scopes.
        service: Authorized MLTools orchestration service.

    Returns:
        Identifier and initial status of the persisted job.

    Raises:
        HTTPException: If authorization fails or MLTools rejects the request.
    """
    try:
        return await service.create_job(user, project_id, body)
    except Exception as exc:
        _raise_mltools_error(exc)


@router.get("", response_model=MLToolsJobListDTO)
async def list_mltools_jobs(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes([ProjectActions.VIEW_EXPERIMENT, ProjectActions.VIEW_METRIC])),
    service: MLToolsService = Depends(get_mltools_service),
):
    """List hyperparameter-importance jobs for a project.

    Args:
        project_id: Project whose job history is requested.
        limit: Maximum number of jobs to return.
        offset: Number of newest jobs to skip.
        user: Authenticated user resolved from a session or API token.
        _: Dependency result used solely to enforce API-token scopes.
        service: Authorized MLTools orchestration service.

    Returns:
        Paginated project job history in newest-first order.

    Raises:
        HTTPException: If authorization fails or MLTools cannot serve the list.
    """
    try:
        return await service.list_jobs(user, project_id, limit, offset)
    except Exception as exc:
        _raise_mltools_error(exc)


@router.get("/{job_id}", response_model=MLToolsJobDTO)
async def get_mltools_job(
    project_id: UUID,
    job_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes([ProjectActions.VIEW_EXPERIMENT, ProjectActions.VIEW_METRIC])
    ),
    service: MLToolsService = Depends(get_mltools_service),
):
    """Return one importance job after verifying project read permissions.

    Args:
        project_id: Project expected to own the job.
        job_id: Importance job identifier.
        user: Authenticated user resolved from a session or API token.
        _: Dependency result used solely to enforce API-token scopes.
        service: Authorized MLTools orchestration service.

    Returns:
        Current job state, progress, configuration, and timestamps.

    Raises:
        HTTPException: If access is denied, the job is foreign, or MLTools fails.
    """
    try:
        return await service.get_job(user, project_id, job_id)
    except Exception as exc:
        _raise_mltools_error(exc)


@router.get("/{job_id}/results", response_model=MLToolsResultsDTO)
async def get_mltools_results(
    project_id: UUID,
    job_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes([ProjectActions.VIEW_EXPERIMENT, ProjectActions.VIEW_METRIC])
    ),
    service: MLToolsService = Depends(get_mltools_service),
):
    """Return ranked hyperparameter-importance results for one job.

    Args:
        project_id: Project expected to own the job.
        job_id: Importance job identifier.
        user: Authenticated user resolved from a session or API token.
        _: Dependency result used solely to enforce API-token scopes.
        service: Authorized MLTools orchestration service.

    Returns:
        Per-target-metric importance results and model-quality metadata.

    Raises:
        HTTPException: If access is denied, the job is foreign, or MLTools fails.
    """
    try:
        return await service.get_results(user, project_id, job_id)
    except Exception as exc:
        _raise_mltools_error(exc)


@router.get("/{job_id}/messages", response_model=MLToolsMessagesDTO)
async def get_mltools_messages(
    project_id: UUID,
    job_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(
        require_api_token_scopes([ProjectActions.VIEW_EXPERIMENT, ProjectActions.VIEW_METRIC])
    ),
    service: MLToolsService = Depends(get_mltools_service),
):
    """Return warnings and errors recorded while processing one job.

    Args:
        project_id: Project expected to own the job.
        job_id: Importance job identifier.
        user: Authenticated user resolved from a session or API token.
        _: Dependency result used solely to enforce API-token scopes.
        service: Authorized MLTools orchestration service.

    Returns:
        Ordered diagnostic messages persisted by the MLTools worker.

    Raises:
        HTTPException: If access is denied, the job is foreign, or MLTools fails.
    """
    try:
        return await service.get_messages(user, project_id, job_id)
    except Exception as exc:
        _raise_mltools_error(exc)
