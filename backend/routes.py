from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional

from .storage import storage
from .schemas import (
    Project, ProjectCreate, ProjectUpdate,
    Experiment, ExperimentCreate, ExperimentUpdate,
    Hypothesis, HypothesisCreate, HypothesisUpdate,
    Metric, MetricCreate,
    DashboardStats, ExperimentReorder
)

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats():
    return storage.get_dashboard_stats()


@router.get("/projects", response_model=List[Project])
def get_all_projects():
    return storage.get_all_projects()


@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/experiments", response_model=List[Experiment])
def get_project_experiments(project_id: str):
    return storage.get_experiments_by_project(project_id)


@router.get("/projects/{project_id}/hypotheses", response_model=List[Hypothesis])
def get_project_hypotheses(project_id: str):
    return storage.get_hypotheses_by_project(project_id)


@router.post("/projects", response_model=Project, status_code=201)
def create_project(data: ProjectCreate):
    return storage.create_project(data)


@router.patch("/projects/{project_id}", response_model=Project)
def update_project(project_id: str, data: ProjectUpdate):
    project = storage.update_project(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    if not storage.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return None


@router.get("/experiments", response_model=List[Experiment])
def get_all_experiments():
    return storage.get_all_experiments()


@router.get("/experiments/recent", response_model=List[Experiment])
def get_recent_experiments(limit: int = 10):
    return storage.get_recent_experiments(limit)


@router.get("/experiments/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: str):
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/experiments/{experiment_id}/metrics", response_model=List[Metric])
def get_experiment_metrics(experiment_id: str):
    return storage.get_metrics_by_experiment(experiment_id)


@router.post("/experiments", response_model=Experiment, status_code=201)
def create_experiment(data: ExperimentCreate):
    return storage.create_experiment(data)


@router.patch("/experiments/{experiment_id}", response_model=Experiment)
def update_experiment(experiment_id: str, data: ExperimentUpdate):
    experiment = storage.update_experiment(experiment_id, data)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.delete("/experiments/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str):
    if not storage.delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return None


@router.patch("/projects/{project_id}/experiments/reorder", response_model=List[Experiment])
def reorder_experiments(project_id: str, data: ExperimentReorder):
    for i, exp_id in enumerate(data.experimentIds):
        from .schemas import ExperimentUpdate as ExpUpdate
        storage.update_experiment(exp_id, ExpUpdate(order=i))
    return storage.get_experiments_by_project(project_id)


@router.get("/hypotheses", response_model=List[Hypothesis])
def get_all_hypotheses():
    return storage.get_all_hypotheses()


@router.get("/hypotheses/recent", response_model=List[Hypothesis])
def get_recent_hypotheses(limit: int = 10):
    return storage.get_recent_hypotheses(limit)


@router.get("/hypotheses/{hypothesis_id}", response_model=Hypothesis)
def get_hypothesis(hypothesis_id: str):
    hypothesis = storage.get_hypothesis(hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis


@router.get("/hypotheses/{hypothesis_id}/experiments", response_model=List[Hypothesis])
def get_hypothesis_experiments(hypothesis_id: str):
    return storage.get_hypotheses_by_experiment(hypothesis_id)


@router.post("/hypotheses", response_model=Hypothesis, status_code=201)
def create_hypothesis(data: HypothesisCreate):
    return storage.create_hypothesis(data)


@router.patch("/hypotheses/{hypothesis_id}", response_model=Hypothesis)
def update_hypothesis(hypothesis_id: str, data: HypothesisUpdate):
    hypothesis = storage.update_hypothesis(hypothesis_id, data)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis


@router.delete("/hypotheses/{hypothesis_id}", status_code=204)
def delete_hypothesis(hypothesis_id: str):
    if not storage.delete_hypothesis(hypothesis_id):
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return None


@router.post("/metrics", response_model=Metric, status_code=201)
def create_metric(data: MetricCreate):
    return storage.create_metric(data)


@router.get("/projects/{project_id}/metrics", response_model=Dict[str, Dict[str, Optional[float]]])
def get_project_metrics(project_id: str):
    return storage.get_aggregated_metrics_for_project(project_id)
