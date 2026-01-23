from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.metrics.repository import MetricRepository
from models import Metric as MetricModel
from models import MetricDirection, Project, User, Experiment


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Repo Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Metric repo project",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_experiment(
    db_session: AsyncSession, project: Project, name: str
) -> Experiment:
    experiment = Experiment(
        project_id=project.id,
        name=name,
        description="Metric experiment",
    )
    db_session.add(experiment)
    await db_session.flush()
    await db_session.refresh(experiment)
    return experiment


async def _create_metric(
    db_session: AsyncSession,
    experiment: Experiment,
    name: str,
    created_at: datetime | None = None,
) -> MetricModel:
    metric = MetricModel(
        experiment_id=experiment.id,
        name=name,
        value=0.9,
        step=0,
        direction=MetricDirection.MAXIMIZE,
        created_at=created_at,
    )
    db_session.add(metric)
    await db_session.flush()
    await db_session.refresh(metric)
    return metric


class TestMetricRepository:
    @pytest.fixture
    def metric_repository(self, db_session: AsyncSession) -> MetricRepository:
        return MetricRepository(db_session)

    async def test_get_metrics_by_experiment_filters(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment_a = await _create_experiment(db_session, project, name="A")
        experiment_b = await _create_experiment(db_session, project, name="B")
        await _create_metric(db_session, experiment_a, name="accuracy")
        await _create_metric(db_session, experiment_b, name="loss")

        metrics = await metric_repository.get_metrics_by_experiment(experiment_a.id)

        names = {metric.name for metric in metrics}
        assert names == {"accuracy"}

    async def test_get_metrics_by_experiment_orders_desc(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, name="A")
        await _create_metric(
            db_session, experiment, name="Older", created_at=datetime(2024, 1, 1)
        )
        await _create_metric(
            db_session, experiment, name="Newer", created_at=datetime(2024, 1, 2)
        )

        metrics = await metric_repository.get_metrics_by_experiment(experiment.id)

        names = [metric.name for metric in metrics]
        assert names == ["Newer", "Older"]
