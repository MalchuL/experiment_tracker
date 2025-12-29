import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Project, Experiment, Hypothesis, Metric, Team,
    ExperimentStatus, HypothesisStatus, MetricDirection,
    team_members, User
)
from .schemas import (
    ProjectCreate, ProjectUpdate,
    ExperimentCreate, ExperimentUpdate,
    HypothesisCreate, HypothesisUpdate,
    MetricCreate, DashboardStats,
    Project as ProjectSchema,
    Experiment as ExperimentSchema,
    Hypothesis as HypothesisSchema,
    Metric as MetricSchema,
    EXPERIMENT_COLORS
)


def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _project_to_schema(project: Project) -> dict:
    # Handle owner name safely
    owner_name = "Unknown"
    if project.owner:
        owner_name = project.owner.display_name or project.owner.email or "Unknown"

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "owner": owner_name,
        "createdAt": _format_datetime(project.created_at),
        "experimentCount": len(project.experiments) if project.experiments else 0,
        "hypothesisCount": len(project.hypotheses) if project.hypotheses else 0,
        "metrics": project.metrics or [],
        "settings": project.settings or {"namingPattern": "{num}_from_{parent}_{change}", "displayMetrics": []},
        "teamId": str(project.team_id) if project.team_id else None,
        "teamName": project.team.name if project.team else None,
    }


def _experiment_to_schema(exp: Experiment) -> dict:
    return {
        "id": str(exp.id),
        "projectId": str(exp.project_id),
        "name": exp.name,
        "description": exp.description,
        "status": exp.status.value,
        "parentExperimentId": str(exp.parent_experiment_id) if exp.parent_experiment_id else None,
        "rootExperimentId": str(exp.root_experiment_id) if exp.root_experiment_id else None,
        "features": exp.features or {},
        "featuresDiff": exp.features_diff,
        "gitDiff": exp.git_diff,
        "progress": exp.progress,
        "color": exp.color,
        "order": exp.order,
        "createdAt": _format_datetime(exp.created_at),
        "startedAt": _format_datetime(exp.started_at),
        "completedAt": _format_datetime(exp.completed_at),
    }


def _hypothesis_to_schema(hyp: Hypothesis) -> dict:
    return {
        "id": str(hyp.id),
        "projectId": str(hyp.project_id),
        "title": hyp.title,
        "description": hyp.description,
        "author": hyp.author,
        "status": hyp.status.value,
        "targetMetrics": hyp.target_metrics or [],
        "baseline": hyp.baseline,
        "createdAt": _format_datetime(hyp.created_at),
        "updatedAt": _format_datetime(hyp.updated_at),
    }


def _metric_to_schema(metric: Metric) -> dict:
    return {
        "id": str(metric.id),
        "experimentId": str(metric.experiment_id),
        "name": metric.name,
        "value": metric.value,
        "step": metric.step,
        "direction": metric.direction.value,
        "createdAt": _format_datetime(metric.created_at),
    }


async def get_user_team_ids(session: AsyncSession, user_id: uuid.UUID) -> List[uuid.UUID]:
    result = await session.execute(
        select(team_members.c.team_id).where(team_members.c.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_accessible_projects(session: AsyncSession, user: User) -> List[dict]:
    team_ids = await get_user_team_ids(session, user.id)

    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))

    query = select(Project).options(
        selectinload(Project.owner),
        selectinload(Project.experiments),
        selectinload(Project.hypotheses),
        selectinload(Project.team)
    ).where(or_(*conditions)).order_by(Project.created_at.desc())

    result = await session.execute(query)
    projects = result.scalars().all()
    return [_project_to_schema(p) for p in projects]


async def get_project_if_accessible(session: AsyncSession, user: User, project_id: str) -> Optional[Project]:
    team_ids = await get_user_team_ids(session, user.id)

    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))

    query = select(Project).options(
        selectinload(Project.owner),
        selectinload(Project.experiments),
        selectinload(Project.hypotheses),
        selectinload(Project.team)
    ).where(
        Project.id == uuid.UUID(project_id),
        or_(*conditions)
    )

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_project(session: AsyncSession, user: User, data: ProjectCreate, team_id_str: Optional[str] = None) -> dict:
    team_id = None
    if team_id_str:
        team_ids = await get_user_team_ids(session, user.id)
        team_uuid = uuid.UUID(team_id_str)
        if team_uuid in team_ids:
            team_id = team_uuid
    
    metrics_list = []
    if hasattr(data, 'metrics') and data.metrics:
        metrics_list = [m.model_dump() if hasattr(m, 'model_dump') else m for m in data.metrics]
    
    settings_dict = {"namingPattern": "{num}_from_{parent}_{change}", "displayMetrics": []}
    if hasattr(data, 'settings') and data.settings:
        settings_dict = data.settings.model_dump() if hasattr(data.settings, 'model_dump') else data.settings
    
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=user.id,
        team_id=team_id,
        metrics=metrics_list,
        settings=settings_dict,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return _project_to_schema(project)


async def update_project(session: AsyncSession, user: User, project_id: str, data: ProjectUpdate) -> Optional[dict]:
    project = await get_project_if_accessible(session, user, project_id)
    if not project:
        return None
    
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.metrics is not None:
        project.metrics = [m.model_dump() for m in data.metrics]
    if data.settings is not None:
        project.settings = data.settings.model_dump()
    
    await session.commit()
    await session.refresh(project)
    return _project_to_schema(project)


async def delete_project(session: AsyncSession, user: User, project_id: str) -> bool:
    project = await get_project_if_accessible(session, user, project_id)
    if not project:
        return False
    
    await session.delete(project)
    await session.commit()
    return True


async def get_accessible_experiments(session: AsyncSession, user: User) -> List[dict]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Experiment).join(Project).where(or_(*conditions)).order_by(Experiment.created_at.desc())
    
    result = await session.execute(query)
    experiments = result.scalars().all()
    return [_experiment_to_schema(e) for e in experiments]


async def get_experiments_by_project(session: AsyncSession, user: User, project_id: str) -> List[dict]:
    project = await get_project_if_accessible(session, user, project_id)
    if not project:
        return []
    
    query = select(Experiment).where(
        Experiment.project_id == uuid.UUID(project_id)
    ).order_by(Experiment.order)
    
    result = await session.execute(query)
    experiments = result.scalars().all()
    return [_experiment_to_schema(e) for e in experiments]


async def get_experiment_if_accessible(session: AsyncSession, user: User, experiment_id: str) -> Optional[Experiment]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Experiment).join(Project).where(
        Experiment.id == uuid.UUID(experiment_id),
        or_(*conditions)
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_experiment(session: AsyncSession, user: User, data: ExperimentCreate) -> Optional[dict]:
    project = await get_project_if_accessible(session, user, data.projectId)
    if not project:
        return None
    
    exp_count = await session.execute(
        select(func.count(Experiment.id)).where(Experiment.project_id == project.id)
    )
    order = exp_count.scalar() or 0
    color = EXPERIMENT_COLORS[order % len(EXPERIMENT_COLORS)]
    
    root_id = None
    features_diff = None
    if data.parentExperimentId:
        parent = await get_experiment_if_accessible(session, user, data.parentExperimentId)
        if parent:
            root_id = parent.root_experiment_id or parent.id
            if data.features and parent.features:
                features_diff = {}
                for key, value in data.features.items():
                    if key not in parent.features or parent.features[key] != value:
                        features_diff[key] = {"old": parent.features.get(key), "new": value}
    
    experiment = Experiment(
        project_id=project.id,
        name=data.name,
        description=data.description or "",
        status=ExperimentStatus(data.status.value if data.status else "planned"),
        parent_experiment_id=uuid.UUID(data.parentExperimentId) if data.parentExperimentId else None,
        root_experiment_id=root_id,
        features=data.features or {},
        features_diff=features_diff,
        git_diff=data.gitDiff,
        color=data.color or color,
        order=data.order if data.order is not None else order,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)
    return _experiment_to_schema(experiment)


async def update_experiment(session: AsyncSession, user: User, experiment_id: str, data: ExperimentUpdate) -> Optional[dict]:
    experiment = await get_experiment_if_accessible(session, user, experiment_id)
    if not experiment:
        return None
    
    if data.name is not None:
        experiment.name = data.name
    if data.description is not None:
        experiment.description = data.description
    if data.status is not None:
        experiment.status = ExperimentStatus(data.status.value)
        if data.status.value == "running" and not experiment.started_at:
            experiment.started_at = datetime.utcnow()
        elif data.status.value in ["complete", "failed"] and not experiment.completed_at:
            experiment.completed_at = datetime.utcnow()
    if data.features is not None:
        experiment.features = data.features
    if data.gitDiff is not None:
        experiment.git_diff = data.gitDiff
    if data.progress is not None:
        experiment.progress = data.progress
    if data.order is not None:
        experiment.order = data.order
    
    await session.commit()
    await session.refresh(experiment)
    return _experiment_to_schema(experiment)


async def delete_experiment(session: AsyncSession, user: User, experiment_id: str) -> bool:
    experiment = await get_experiment_if_accessible(session, user, experiment_id)
    if not experiment:
        return False
    
    await session.delete(experiment)
    await session.commit()
    return True


async def get_accessible_hypotheses(session: AsyncSession, user: User) -> List[dict]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Hypothesis).join(Project).where(or_(*conditions)).order_by(Hypothesis.created_at.desc())
    
    result = await session.execute(query)
    hypotheses = result.scalars().all()
    return [_hypothesis_to_schema(h) for h in hypotheses]


async def get_hypotheses_by_project(session: AsyncSession, user: User, project_id: str) -> List[dict]:
    project = await get_project_if_accessible(session, user, project_id)
    if not project:
        return []
    
    query = select(Hypothesis).where(
        Hypothesis.project_id == uuid.UUID(project_id)
    ).order_by(Hypothesis.created_at.desc())
    
    result = await session.execute(query)
    hypotheses = result.scalars().all()
    return [_hypothesis_to_schema(h) for h in hypotheses]


async def get_hypothesis_if_accessible(session: AsyncSession, user: User, hypothesis_id: str) -> Optional[Hypothesis]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Hypothesis).join(Project).where(
        Hypothesis.id == uuid.UUID(hypothesis_id),
        or_(*conditions)
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_hypothesis(session: AsyncSession, user: User, data: HypothesisCreate) -> Optional[dict]:
    project = await get_project_if_accessible(session, user, data.projectId)
    if not project:
        return None
    
    hypothesis = Hypothesis(
        project_id=project.id,
        title=data.title,
        description=data.description or "",
        author=data.author,
        status=HypothesisStatus(data.status.value if data.status else "proposed"),
        target_metrics=data.targetMetrics or [],
        baseline=data.baseline or "root",
    )
    session.add(hypothesis)
    await session.commit()
    await session.refresh(hypothesis)
    return _hypothesis_to_schema(hypothesis)


async def update_hypothesis(session: AsyncSession, user: User, hypothesis_id: str, data: HypothesisUpdate) -> Optional[dict]:
    hypothesis = await get_hypothesis_if_accessible(session, user, hypothesis_id)
    if not hypothesis:
        return None
    
    if data.title is not None:
        hypothesis.title = data.title
    if data.description is not None:
        hypothesis.description = data.description
    if data.author is not None:
        hypothesis.author = data.author
    if data.status is not None:
        hypothesis.status = HypothesisStatus(data.status.value)
    if data.targetMetrics is not None:
        hypothesis.target_metrics = data.targetMetrics
    if data.baseline is not None:
        hypothesis.baseline = data.baseline
    
    await session.commit()
    await session.refresh(hypothesis)
    return _hypothesis_to_schema(hypothesis)


async def delete_hypothesis(session: AsyncSession, user: User, hypothesis_id: str) -> bool:
    hypothesis = await get_hypothesis_if_accessible(session, user, hypothesis_id)
    if not hypothesis:
        return False
    
    await session.delete(hypothesis)
    await session.commit()
    return True


async def get_experiment_metrics(session: AsyncSession, user: User, experiment_id: str) -> List[dict]:
    experiment = await get_experiment_if_accessible(session, user, experiment_id)
    if not experiment:
        return []
    
    query = select(Metric).where(
        Metric.experiment_id == uuid.UUID(experiment_id)
    ).order_by(Metric.step)
    
    result = await session.execute(query)
    metrics = result.scalars().all()
    return [_metric_to_schema(m) for m in metrics]


async def create_metric(session: AsyncSession, user: User, data: MetricCreate) -> Optional[dict]:
    experiment = await get_experiment_if_accessible(session, user, data.experimentId)
    if not experiment:
        return None
    
    metric = Metric(
        experiment_id=experiment.id,
        name=data.name,
        value=data.value,
        step=data.step,
        direction=MetricDirection(data.direction.value if data.direction else "minimize"),
    )
    session.add(metric)
    await session.commit()
    await session.refresh(metric)
    return _metric_to_schema(metric)


async def get_dashboard_stats(session: AsyncSession, user: User) -> dict:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    project_filter = or_(*conditions)
    
    projects_count = await session.execute(
        select(func.count(Project.id)).where(project_filter)
    )
    
    experiments_query = select(Experiment).join(Project).where(project_filter)
    experiments_result = await session.execute(experiments_query)
    experiments = experiments_result.scalars().all()
    
    hypotheses_query = select(Hypothesis).join(Project).where(project_filter)
    hypotheses_result = await session.execute(hypotheses_query)
    hypotheses = hypotheses_result.scalars().all()
    
    return {
        "totalProjects": projects_count.scalar() or 0,
        "totalExperiments": len(experiments),
        "runningExperiments": sum(1 for e in experiments if e.status == ExperimentStatus.RUNNING),
        "completedExperiments": sum(1 for e in experiments if e.status == ExperimentStatus.COMPLETE),
        "failedExperiments": sum(1 for e in experiments if e.status == ExperimentStatus.FAILED),
        "totalHypotheses": len(hypotheses),
        "supportedHypotheses": sum(1 for h in hypotheses if h.status == HypothesisStatus.SUPPORTED),
        "refutedHypotheses": sum(1 for h in hypotheses if h.status == HypothesisStatus.REFUTED),
    }


async def get_recent_experiments(session: AsyncSession, user: User, limit: int = 10) -> List[dict]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Experiment).join(Project).where(or_(*conditions)).order_by(Experiment.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    experiments = result.scalars().all()
    return [_experiment_to_schema(e) for e in experiments]


async def get_recent_hypotheses(session: AsyncSession, user: User, limit: int = 10) -> List[dict]:
    team_ids = await get_user_team_ids(session, user.id)
    
    conditions = [Project.owner_id == user.id]
    if team_ids:
        conditions.append(Project.team_id.in_(team_ids))
    
    query = select(Hypothesis).join(Project).where(or_(*conditions)).order_by(Hypothesis.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    hypotheses = result.scalars().all()
    return [_hypothesis_to_schema(h) for h in hypotheses]
