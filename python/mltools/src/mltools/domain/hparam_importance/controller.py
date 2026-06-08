"""Expose internal HTTP endpoints for hparam-importance job operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from mltools.api.dependencies import get_job_service
from mltools.domain.hparam_importance.dto import CreateJobDTO, CreateJobResponseDTO, JobDTO, JobListDTO, MessagesDTO, ResultsDTO
from mltools.domain.hparam_importance.repository import JobNotFoundError
from mltools.domain.hparam_importance.service import JobService

router = APIRouter()

def raise_http(error: Exception) -> None:
    """Translate domain/application errors into internal HTTP responses.

    Args:
        error: Exception raised while serving an internal job request.

    Raises:
        HTTPException: ``404`` for missing project-scoped jobs and ``400`` for other
        request or service errors.
    """
    if isinstance(error, JobNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("/projects/{project_id}/hparams/importance/jobs", response_model=CreateJobResponseDTO)
async def create_job(project_id: UUID, payload: CreateJobDTO, service: JobService = Depends(get_job_service)):
    """Create and asynchronously dispatch a project importance job.

    Args:
        project_id: Project whose experiments should be analyzed.
        payload: Target metrics, exclusions, and parameter-processing overrides.
        service: Injected job application service.

    Returns:
        CreateJobResponseDTO: Persisted job identifier and initial status.
    """
    try:
        return await service.create(project_id, payload)
    except Exception as exc:
        raise_http(exc)


@router.get("/projects/{project_id}/hparams/importance/jobs", response_model=JobListDTO)
async def list_jobs(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: JobService = Depends(get_job_service),
):
    """List project importance-job history.

    Args:
        project_id: Project whose jobs are requested.
        limit: Maximum jobs to return.
        offset: Number of newest jobs to skip.
        service: Injected job application service.

    Returns:
        JobListDTO: Paginated job history.
    """
    return await service.list(project_id, limit, offset)


@router.get("/projects/{project_id}/hparams/importance/jobs/{job_id}", response_model=JobDTO)
async def get_job(project_id: UUID, job_id: UUID, service: JobService = Depends(get_job_service)):
    """Return current lifecycle metadata for one project-scoped job.

    Args:
        project_id: Project that must own the job.
        job_id: Job identifier.
        service: Injected job application service.

    Returns:
        JobDTO: Current status, stage, progress, configuration targets, and timing.
    """
    try:
        return await service.get(project_id, job_id)
    except Exception as exc:
        raise_http(exc)


@router.get("/projects/{project_id}/hparams/importance/jobs/{job_id}/results", response_model=ResultsDTO)
async def get_results(project_id: UUID, job_id: UUID, service: JobService = Depends(get_job_service)):
    """Return grouped ranked results for one job.

    Args:
        project_id: Project that must own the job.
        job_id: Job identifier.
        service: Injected job application service.

    Returns:
        ResultsDTO: Ranked hyperparameter importance grouped by target metric.
    """
    try:
        return await service.results(project_id, job_id)
    except Exception as exc:
        raise_http(exc)


@router.get("/projects/{project_id}/hparams/importance/jobs/{job_id}/messages", response_model=MessagesDTO)
async def get_messages(project_id: UUID, job_id: UUID, service: JobService = Depends(get_job_service)):
    """Return ordered diagnostics for one job.

    Args:
        project_id: Project that must own the job.
        job_id: Job identifier.
        service: Injected job application service.

    Returns:
        MessagesDTO: Persisted informational, warning, and error messages.
    """
    try:
        return await service.messages(project_id, job_id)
    except Exception as exc:
        raise_http(exc)
"""Trusted internal FastAPI routes for hyperparameter-importance jobs."""
