from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional

from .storage import storage
from .schemas import (
    Project, ProjectCreate, ProjectUpdate,
    Experiment, ExperimentCreate, ExperimentUpdate,
    Hypothesis, HypothesisCreate, HypothesisUpdate,
    Metric, MetricCreate,
    DashboardStats, ExperimentReorder
)
from .auth import current_active_user
from .models import User

router = APIRouter(dependencies=[Depends(current_active_user)])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(user: User = Depends(current_active_user)):
    return storage.get_dashboard_stats()


@router.get("/projects", response_model=List[Project])
async def get_all_projects(user: User = Depends(current_active_user)):
    return storage.get_all_projects()


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str, user: User = Depends(current_active_user)):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/experiments", response_model=List[Experiment])
async def get_project_experiments(project_id: str, user: User = Depends(current_active_user)):
    return storage.get_experiments_by_project(project_id)


@router.get("/projects/{project_id}/hypotheses", response_model=List[Hypothesis])
async def get_project_hypotheses(project_id: str, user: User = Depends(current_active_user)):
    return storage.get_hypotheses_by_project(project_id)


@router.get("/projects/{project_id}/all-metrics", response_model=Dict[str, List[Metric]])
async def get_project_all_metrics(project_id: str, user: User = Depends(current_active_user)):
    """Get all metrics for all experiments in a project, grouped by experiment ID."""
    experiments = storage.get_experiments_by_project(project_id)
    result = {}
    for exp in experiments:
        result[exp.id] = storage.get_metrics_by_experiment(exp.id)
    return result


@router.post("/projects", response_model=Project, status_code=201)
async def create_project(data: ProjectCreate, user: User = Depends(current_active_user)):
    return storage.create_project(data)


@router.patch("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, data: ProjectUpdate, user: User = Depends(current_active_user)):
    project = storage.update_project(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, user: User = Depends(current_active_user)):
    if not storage.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return None


@router.get("/experiments", response_model=List[Experiment])
async def get_all_experiments(user: User = Depends(current_active_user)):
    return storage.get_all_experiments()


@router.get("/experiments/recent", response_model=List[Experiment])
async def get_recent_experiments(limit: int = 10, user: User = Depends(current_active_user)):
    return storage.get_recent_experiments(limit)


@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(experiment_id: str, user: User = Depends(current_active_user)):
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/experiments/{experiment_id}/metrics", response_model=List[Metric])
async def get_experiment_metrics(experiment_id: str, user: User = Depends(current_active_user)):
    return storage.get_metrics_by_experiment(experiment_id)


@router.post("/experiments", response_model=Experiment, status_code=201)
async def create_experiment(data: ExperimentCreate, user: User = Depends(current_active_user)):
    return storage.create_experiment(data)


@router.patch("/experiments/{experiment_id}", response_model=Experiment)
async def update_experiment(experiment_id: str, data: ExperimentUpdate, user: User = Depends(current_active_user)):
    experiment = storage.update_experiment(experiment_id, data)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.delete("/experiments/{experiment_id}", status_code=204)
async def delete_experiment(experiment_id: str, user: User = Depends(current_active_user)):
    if not storage.delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return None


@router.patch("/projects/{project_id}/experiments/reorder", response_model=List[Experiment])
async def reorder_experiments(project_id: str, data: ExperimentReorder, user: User = Depends(current_active_user)):
    for i, exp_id in enumerate(data.experimentIds):
        from .schemas import ExperimentUpdate as ExpUpdate
        storage.update_experiment(exp_id, ExpUpdate(order=i))
    return storage.get_experiments_by_project(project_id)


@router.get("/hypotheses", response_model=List[Hypothesis])
async def get_all_hypotheses(user: User = Depends(current_active_user)):
    return storage.get_all_hypotheses()


@router.get("/hypotheses/recent", response_model=List[Hypothesis])
async def get_recent_hypotheses(limit: int = 10, user: User = Depends(current_active_user)):
    return storage.get_recent_hypotheses(limit)


@router.get("/hypotheses/{hypothesis_id}", response_model=Hypothesis)
async def get_hypothesis(hypothesis_id: str, user: User = Depends(current_active_user)):
    hypothesis = storage.get_hypothesis(hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis


@router.get("/hypotheses/{hypothesis_id}/experiments", response_model=List[Hypothesis])
async def get_hypothesis_experiments(hypothesis_id: str, user: User = Depends(current_active_user)):
    return storage.get_hypotheses_by_experiment(hypothesis_id)


@router.post("/hypotheses", response_model=Hypothesis, status_code=201)
async def create_hypothesis(data: HypothesisCreate, user: User = Depends(current_active_user)):
    return storage.create_hypothesis(data)


@router.patch("/hypotheses/{hypothesis_id}", response_model=Hypothesis)
async def update_hypothesis(hypothesis_id: str, data: HypothesisUpdate, user: User = Depends(current_active_user)):
    hypothesis = storage.update_hypothesis(hypothesis_id, data)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis


@router.delete("/hypotheses/{hypothesis_id}", status_code=204)
async def delete_hypothesis(hypothesis_id: str, user: User = Depends(current_active_user)):
    if not storage.delete_hypothesis(hypothesis_id):
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return None


@router.post("/metrics", response_model=Metric, status_code=201)
async def create_metric(data: MetricCreate, user: User = Depends(current_active_user)):
    return storage.create_metric(data)


@router.get("/projects/{project_id}/metrics", response_model=Dict[str, Dict[str, Optional[float]]])
async def get_project_metrics(project_id: str, user: User = Depends(current_active_user)):
    return storage.get_aggregated_metrics_for_project(project_id)
