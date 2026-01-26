from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.metrics.dto import MetricCreateDTO, MetricUpdateDTO
from domain.metrics.error import MetricNotAccessibleError, MetricNotFoundError
from domain.metrics.service import MetricService
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Metric as MetricModel
from models import MetricDirection, Project, User, Experiment


async def _create_project(
    db_session: AsyncSession,
    owner: User,
    name: str = "Service Project",
    metrics: list[dict] | None = None,
) -> Project:
    project = Project(
        name=name,
        description="Metric service project",
        owner_id=owner.id,
        team_id=None,
        metrics=metrics or [],
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
        id=None,
        project_id=project.id,
        name=name,
        description="Metric experiment",
    )
    db_session.add(experiment)
    await db_session.flush()
    return experiment


async def _create_metric(
    db_session: AsyncSession,
    experiment: Experiment,
    name: str,
    value: float = 0.9,
    step: int = 1,
    direction: MetricDirection = MetricDirection.MAXIMIZE,
    created_at: datetime | None = None,
) -> MetricModel:
    metric = MetricModel(
        experiment_id=experiment.id,
        name=name,
        value=value,
        step=step,
        direction=direction,
        created_at=created_at,
    )
    db_session.add(metric)
    await db_session.flush()
    return metric


class TestMetricService:
    @pytest.fixture
    def metric_service(self, db_session: AsyncSession) -> MetricService:
        return MetricService(db_session)

    async def test_get_metrics_by_experiment_requires_permission(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        await _create_metric(db_session, experiment, "accuracy")

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.get_metrics_by_experiment(test_user, experiment.id)

    async def test_get_metrics_by_experiment_returns_list(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        await _create_metric(
            db_session, experiment, "Older", created_at=datetime(2024, 1, 1)
        )
        await _create_metric(
            db_session, experiment, "Newer", created_at=datetime(2024, 1, 2)
        )
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_METRIC,
            allowed=True,
            project_id=project.id,
        )

        metrics = await metric_service.get_metrics_by_experiment(
            test_user, experiment.id
        )

        names = [metric.name for metric in metrics]
        assert names == ["Newer", "Older"]

    async def test_get_metrics_by_experiment_missing_experiment_raises(
        self, metric_service: MetricService, test_user: User
    ) -> None:
        with pytest.raises(MetricNotFoundError):
            await metric_service.get_metrics_by_experiment(test_user, uuid4())

    async def test_create_metric_permission_denied(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        dto = MetricCreateDTO(
            experiment_id=experiment.id,
            name="loss",
            value=1.23,
            step=0,
            direction=MetricDirection.MINIMIZE,
        )

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.create_metric(test_user, dto)

    async def test_create_metric_sets_fields(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.CREATE_METRIC,
            allowed=True,
            project_id=project.id,
        )
        dto = MetricCreateDTO(
            experiment_id=experiment.id,
            name="loss",
            value=1.23,
            step=2,
            direction=MetricDirection.MINIMIZE,
        )

        created = await metric_service.create_metric(test_user, dto)

        assert created.id is not None
        assert created.experiment_id == experiment.id
        assert created.name == "loss"
        assert created.value == 1.23
        assert created.step == 2
        assert created.direction == MetricDirection.MINIMIZE

    async def test_update_metric_permission_denied(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric = await _create_metric(db_session, experiment, "accuracy")
        dto = MetricUpdateDTO(value=0.5)

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.update_metric(test_user, metric.id, dto)

    async def test_update_metric_updates_fields(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric = await _create_metric(db_session, experiment, "accuracy")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_METRIC,
            allowed=True,
            project_id=project.id,
        )
        dto = MetricUpdateDTO(value=0.5, step=4)

        updated = await metric_service.update_metric(test_user, metric.id, dto)

        assert updated.value == 0.5
        assert updated.step == 4

    async def test_update_metric_missing_raises(
        self, metric_service: MetricService, test_user: User
    ) -> None:
        dto = MetricUpdateDTO(value=0.4)
        with pytest.raises(MetricNotFoundError):
            await metric_service.update_metric(test_user, uuid4(), dto)

    async def test_delete_metric_permission_denied(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric = await _create_metric(db_session, experiment, "accuracy")

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.delete_metric(test_user, metric.id)

    async def test_delete_metric_removes_metric(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric = await _create_metric(db_session, experiment, "accuracy")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.DELETE_METRIC,
            allowed=True,
            project_id=project.id,
        )

        deleted = await metric_service.delete_metric(test_user, metric.id)

        assert deleted is True
        assert await db_session.get(MetricModel, metric.id) is None

    async def test_get_aggregated_metrics_for_project_requires_permission(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.get_aggregated_metrics_for_project(
                test_user, project.id
            )

    async def test_get_aggregated_metrics_for_project_selects_aggregates(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_metrics = [
            {
                "name": "accuracy",
                "aggregation": "last",
                "direction": "maximize",
            },
            {
                "name": "loss",
                "aggregation": "best",
                "direction": "minimize",
            },
            {
                "name": "score",
                "aggregation": "best",
                "direction": "maximize",
            },
        ]
        project = await _create_project(db_session, test_user, metrics=project_metrics)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric_accuracy_last = await _create_metric(
            db_session, experiment, "accuracy", value=0.5, step=1
        )
        metric_accuracy_latest = await _create_metric(
            db_session, experiment, "accuracy", value=0.6, step=2
        )
        metric_loss_worse = await _create_metric(
            db_session, experiment, "loss", value=0.3, step=1
        )
        metric_loss_best = await _create_metric(
            db_session, experiment, "loss", value=0.2, step=2
        )
        metric_score_worse = await _create_metric(
            db_session, experiment, "score", value=0.4, step=1
        )
        metric_score_best = await _create_metric(
            db_session, experiment, "score", value=0.9, step=2
        )

        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_METRIC,
            allowed=True,
            project_id=project.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        result = await metric_service.get_aggregated_metrics_for_project(
            test_user, project.id
        )

        assert experiment.id in result
        experiment_metrics = result[experiment.id]
        assert set(experiment_metrics.keys()) == {"accuracy", "loss", "score"}
        assert experiment_metrics["accuracy"].id == metric_accuracy_latest.id
        assert experiment_metrics["accuracy"].value == metric_accuracy_latest.value
        assert experiment_metrics["loss"].id == metric_loss_best.id
        assert experiment_metrics["score"].id == metric_score_best.id
        assert experiment_metrics["loss"].id != metric_loss_worse.id
        assert experiment_metrics["accuracy"].id != metric_accuracy_last.id
        assert experiment_metrics["score"].id != metric_score_worse.id

    async def test_get_aggregated_metrics_for_project_average_raises(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_metrics = [
            {
                "name": "average_metric",
                "aggregation": "average",
                "direction": "maximize",
            }
        ]
        project = await _create_project(db_session, test_user, metrics=project_metrics)
        experiment = await _create_experiment(db_session, project, "Experiment")
        await _create_metric(
            db_session, experiment, "average_metric", value=0.4, step=1
        )

        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_METRIC,
            allowed=True,
            project_id=project.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )

        with pytest.raises(NotImplementedError):
            await metric_service.get_aggregated_metrics_for_project(
                test_user, project.id
            )
