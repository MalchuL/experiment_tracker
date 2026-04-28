from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.metrics.dto import MetricUpsertDTO
from domain.metrics.error import MetricNotAccessibleError, MetricNotFoundError
from domain.metrics.service import MetricService
from domain.projects.service import ProjectService
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Metric as MetricModel
from models import Project, User, Experiment


async def _create_project(
    db_session: AsyncSession,
    owner: User,
    name: str = "Service Project",
    metrics: list[dict] | None = None,
) -> Project:
    metrics_payload = metrics or {"tracked_metrics": [], "display_metrics": []}
    project = Project(
        name=name,
        description="Metric service project",
        owner_id=owner.id,
        team_id=None,
        metrics=metrics_payload,
        settings=[],
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
    label: str | None = None,
    created_at: datetime | None = None,
) -> MetricModel:
    metric = MetricModel(
        experiment_id=experiment.id,
        name=name,
        value=value,
        label=label,
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

        names = [metric.name for metric in metrics.data]
        assert names == ["Newer", "Older"]

    async def test_get_metrics_by_experiment_missing_experiment_raises(
        self, metric_service: MetricService, test_user: User
    ) -> None:
        with pytest.raises(MetricNotFoundError):
            await metric_service.get_metrics_by_experiment(test_user, uuid4())

    async def test_upsert_metric_create_branch_permission_denied(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        dto = MetricUpsertDTO(
            experiment_id=experiment.id,
            name="loss",
            value=1.23,
        )

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.upsert_metric(test_user, dto)

    async def test_upsert_metric_creates_new_row(
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
        dto = MetricUpsertDTO(
            experiment_id=experiment.id,
            name="loss",
            value=1.23,
            label="val",
        )

        created = await metric_service.upsert_metric(test_user, dto)

        assert created.id is not None
        assert created.experiment_id == experiment.id
        assert created.name == "loss"
        assert created.value == 1.23
        assert created.label == "val"

    async def test_upsert_metric_empty_label_construct_stored_as_unlabeled(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """model_construct skips DTO validators; service must still coerce '' → None."""
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.CREATE_METRIC,
            allowed=True,
            project_id=project.id,
        )
        dto = MetricUpsertDTO.model_construct(
            experiment_id=experiment.id,
            name="loss",
            value=1.23,
            label="",
        )

        created = await metric_service.upsert_metric(test_user, dto)

        assert created.label is None

    async def test_upsert_metric_update_branch_requires_edit(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        await _create_metric(db_session, experiment, "accuracy", label="train")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.CREATE_METRIC,
            allowed=True,
            project_id=project.id,
        )
        dto = MetricUpsertDTO(
            experiment_id=experiment.id,
            name="accuracy",
            value=0.5,
            label="train",
        )

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.upsert_metric(test_user, dto)

    async def test_upsert_metric_updates_value_when_key_exists(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric = await _create_metric(
            db_session, experiment, "accuracy", value=0.1, label="tuned"
        )
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_METRIC,
            allowed=True,
            project_id=project.id,
        )
        dto = MetricUpsertDTO(
            experiment_id=experiment.id,
            name="accuracy",
            value=0.5,
            label="tuned",
        )

        updated = await metric_service.upsert_metric(test_user, dto)

        assert updated.id == metric.id
        assert updated.value == 0.5
        assert updated.name == "accuracy"
        assert updated.label == "tuned"

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
        project_service = ProjectService(db_session)

        with pytest.raises(MetricNotAccessibleError):
            await metric_service.get_aggregated_metrics_for_project(
                test_user, project.id, project_service
            )

    async def test_get_aggregated_metrics_for_project_selects_aggregates(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_metrics = {
            "tracked_metrics": [
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
            ],
            "display_metrics": [],
        }
        project = await _create_project(db_session, test_user, metrics=project_metrics)
        project_service = ProjectService(db_session)
        experiment = await _create_experiment(db_session, project, "Experiment")
        metric_accuracy = await _create_metric(
            db_session,
            experiment,
            "accuracy",
            value=0.6,
            created_at=datetime(2024, 1, 2, 0, 0, 0),
        )
        metric_loss = await _create_metric(
            db_session,
            experiment,
            "loss",
            value=0.2,
            created_at=datetime(2024, 1, 2, 0, 0, 0),
        )
        metric_score = await _create_metric(
            db_session,
            experiment,
            "score",
            value=0.9,
            created_at=datetime(2024, 1, 2, 0, 0, 0),
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
            test_user, project.id, project_service
        )

        assert len(result.data) == 3
        assert {metric.experiment_id for metric in result.data} == {experiment.id}
        metrics_by_name = {metric.name: metric for metric in result.data}
        assert set(metrics_by_name.keys()) == {"accuracy", "loss", "score"}
        assert metrics_by_name["accuracy"].id == metric_accuracy.id
        assert metrics_by_name["accuracy"].value == 0.6
        assert metrics_by_name["loss"].id == metric_loss.id
        assert metrics_by_name["loss"].value == 0.2
        assert metrics_by_name["score"].id == metric_score.id
        assert metrics_by_name["score"].value == 0.9

    async def test_get_aggregated_metrics_for_project_average_raises(
        self,
        metric_service: MetricService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_metrics = {
            "tracked_metrics": [
                {
                    "name": "average_metric",
                    "aggregation": "average",
                    "direction": "maximize",
                }
            ],
            "display_metrics": [],
        }
        project = await _create_project(db_session, test_user, metrics=project_metrics)
        project_service = ProjectService(db_session)
        experiment = await _create_experiment(db_session, project, "Experiment")
        await _create_metric(
            db_session, experiment, "average_metric", value=0.4, created_at=datetime(2024, 1, 1)
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
                test_user, project.id, project_service
            )
