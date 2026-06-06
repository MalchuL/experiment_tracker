from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.metrics.repository import MetricRepository
from models import Metric as MetricModel
from models import Project, User, Experiment


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
        label=None,
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

        names = {metric.name for metric in metrics.data}
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

        names = [metric.name for metric in metrics.data]
        assert names == ["Newer", "Older"]

    async def test_list_selective_project_metrics_matches_exact_label_and_project(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        other_project = await _create_project(db_session, test_user, name="Other")
        experiment = await _create_experiment(db_session, project, name="A")
        other_experiment = await _create_experiment(db_session, other_project, name="B")
        selected = await _create_metric(db_session, experiment, name="loss")
        labeled = MetricModel(
            experiment_id=experiment.id,
            name="loss",
            value=0.1,
            label="validation",
        )
        foreign = await _create_metric(db_session, other_experiment, name="loss")
        db_session.add(labeled)
        await db_session.flush()

        metrics = await metric_repository.list_selective_project_metrics(
            project.id,
            [("loss", None)],
            [experiment.id, other_experiment.id],
        )

        assert [metric.id for metric in metrics] == [selected.id]
        assert foreign.id not in {metric.id for metric in metrics}
