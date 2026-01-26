from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domain.metrics.dto import MetricCreateDTO, MetricUpdateDTO
from domain.metrics.mapper import MetricMapper
from models import Metric as MetricModel
from models import MetricDirection, Project, User, Experiment


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Mapper Project"
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Metric mapper project",
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
    db_session: AsyncSession, project: Project, name: str = "Experiment"
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
    name: str = "accuracy",
    created_at: datetime | None = None,
) -> MetricModel:
    metric = MetricModel(
        experiment_id=experiment.id,
        name=name,
        value=0.9,
        step=1,
        direction=MetricDirection.MAXIMIZE,
        created_at=created_at,
    )
    db_session.add(metric)
    await db_session.flush()
    await db_session.refresh(metric)
    return metric


class TestMetricMapper:
    async def test_metric_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = MetricMapper()
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project)
        metric = await _create_metric(
            db_session, experiment, name="accuracy", created_at=datetime(2024, 1, 1)
        )

        dto = mapper.metric_schema_to_dto(metric)

        assert dto.id == metric.id
        assert dto.experiment_id == metric.experiment_id
        assert dto.name == "accuracy"
        assert dto.value == 0.9
        assert dto.step == 1
        assert dto.direction == MetricDirection.MAXIMIZE
        assert dto.created_at == datetime(2024, 1, 1)

    async def test_metric_list_schema_to_dto(
        self, db_session: AsyncSession, test_user: User
    ):
        mapper = MetricMapper()
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project)
        metric = await _create_metric(db_session, experiment)

        dtos = mapper.metric_list_schema_to_dto([metric])

        assert len(dtos) == 1
        assert dtos[0].id == metric.id
        assert dtos[0].name == "accuracy"

    def test_metric_create_dto_to_schema(self):
        mapper = MetricMapper()
        dto = MetricCreateDTO(
            experiment_id="223e4567-e89b-12d3-a456-426614174000",
            name="loss",
            value=1.23,
            step=0,
            direction=MetricDirection.MINIMIZE,
        )

        metric = mapper.metric_create_dto_to_schema(dto)

        assert str(metric.experiment_id) == str(dto.experiment_id)
        assert metric.name == "loss"
        assert metric.value == 1.23
        assert metric.step == 0
        assert metric.direction == MetricDirection.MINIMIZE

    def test_metric_update_dto_to_update_dict(self):
        mapper = MetricMapper()
        dto = MetricUpdateDTO(
            name="updated",
            value=0.8,
            step=2,
            direction=MetricDirection.MAXIMIZE,
        )

        updates = mapper.metric_update_dto_to_update_dict(dto)

        assert updates["name"] == "updated"
        assert updates["value"] == 0.8
        assert updates["step"] == 2
        assert updates["direction"] == MetricDirection.MAXIMIZE
