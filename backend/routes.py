from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_async_session
from .schemas import (
    ProjectCreate, ProjectUpdate,
    ExperimentCreate, ExperimentUpdate,
    HypothesisCreate, HypothesisUpdate,
    MetricCreate,
    DashboardStats, ExperimentReorder
)
from .auth import current_active_user
from .models import User
from . import repository

router = APIRouter(dependencies=[Depends(current_active_user)])


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_dashboard_stats(session, user)


@router.get("/projects")
async def get_all_projects(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_accessible_projects(session, user)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    project = await repository.get_project_if_accessible(session, user, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    from .repository import _project_to_schema
    return _project_to_schema(project)


@router.get("/projects/{project_id}/experiments")
async def get_project_experiments(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_experiments_by_project(session, user, project_id)


@router.get("/projects/{project_id}/hypotheses")
async def get_project_hypotheses(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_hypotheses_by_project(session, user, project_id)


@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.create_project(session, user, data, data.teamId)


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.update_project(session, user, project_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    success = await repository.delete_project(session, user, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


@router.get("/experiments")
async def get_all_experiments(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_accessible_experiments(session, user)


@router.get("/experiments/recent")
async def get_recent_experiments(
    limit: int = 10,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_recent_experiments(session, user, limit)


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    experiment = await repository.get_experiment_if_accessible(session, user, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    from .repository import _experiment_to_schema
    return _experiment_to_schema(experiment)


@router.get("/experiments/{experiment_id}/metrics")
async def get_experiment_metrics(
    experiment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_experiment_metrics(session, user, experiment_id)


@router.post("/experiments")
async def create_experiment(
    data: ExperimentCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.create_experiment(session, user, data)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found or not accessible")
    return result


@router.patch("/experiments/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    data: ExperimentUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.update_experiment(session, user, experiment_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    success = await repository.delete_experiment(session, user, experiment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"success": True}


@router.post("/experiments/reorder")
async def reorder_experiments(
    data: ExperimentReorder,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    for i, exp_id in enumerate(data.experimentIds):
        from .schemas import ExperimentUpdate
        await repository.update_experiment(session, user, exp_id, ExperimentUpdate(order=i))
    return {"success": True}


@router.get("/hypotheses")
async def get_all_hypotheses(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_accessible_hypotheses(session, user)


@router.get("/hypotheses/recent")
async def get_recent_hypotheses(
    limit: int = 10,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await repository.get_recent_hypotheses(session, user, limit)


@router.get("/hypotheses/{hypothesis_id}")
async def get_hypothesis(
    hypothesis_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    hypothesis = await repository.get_hypothesis_if_accessible(session, user, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    from .repository import _hypothesis_to_schema
    return _hypothesis_to_schema(hypothesis)


@router.post("/hypotheses")
async def create_hypothesis(
    data: HypothesisCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.create_hypothesis(session, user, data)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found or not accessible")
    return result


@router.patch("/hypotheses/{hypothesis_id}")
async def update_hypothesis(
    hypothesis_id: str,
    data: HypothesisUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.update_hypothesis(session, user, hypothesis_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return result


@router.delete("/hypotheses/{hypothesis_id}")
async def delete_hypothesis(
    hypothesis_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    success = await repository.delete_hypothesis(session, user, hypothesis_id)
    if not success:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return {"success": True}


@router.post("/metrics")
async def create_metric(
    data: MetricCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await repository.create_metric(session, user, data)
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found or not accessible")
    return result
