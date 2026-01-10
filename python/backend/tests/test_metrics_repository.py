"""
Tests for MetricRepository.
"""

import uuid
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from models import Metric, Experiment, Project, User, Team, TeamMember, MetricDirection
from domain.metrics.repository import MetricRepository
from domain.projects.repository import UserProtocol


class TestMetricRepository:
    """Test suite for MetricRepository."""

    @pytest.fixture
    def metric_repository(self, db_session: AsyncSession) -> MetricRepository:
        """Create a MetricRepository instance."""
        return MetricRepository(db_session)

    @pytest.fixture
    async def test_experiment(
        self, db_session: AsyncSession, test_user: User
    ) -> Experiment:
        """Create a test experiment."""
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Test Experiment",
            description="Test experiment description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)
        return experiment

    # CRUD Operations Tests

    async def test_create_metric(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test creating a new metric."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
            direction=MetricDirection.MAXIMIZE,
        )

        created_metric = await metric_repository.create(metric)

        assert created_metric.id is not None
        assert created_metric.name == "accuracy"
        assert created_metric.value == 0.95
        assert created_metric.step == 1
        assert created_metric.experiment_id == test_experiment.id
        assert created_metric.direction == MetricDirection.MAXIMIZE

    async def test_create_metric_with_all_fields(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test creating a metric with all fields."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="loss",
            value=0.05,
            step=100,
            direction=MetricDirection.MINIMIZE,
        )

        created_metric = await metric_repository.create(metric)

        assert created_metric.id is not None
        assert created_metric.name == "loss"
        assert created_metric.value == 0.05
        assert created_metric.step == 100
        assert created_metric.direction == MetricDirection.MINIMIZE

    async def test_create_metric_created_at_is_naive_utc(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test that created_at is a naive UTC datetime."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )

        created_metric = await metric_repository.create(metric)

        assert created_metric.created_at is not None
        assert isinstance(created_metric.created_at, datetime)
        assert created_metric.created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{created_metric.created_at.tzinfo}"
        )

    async def test_get_by_id(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test retrieving a metric by ID using UUID object."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        retrieved_metric = await metric_repository.get_by_id(metric.id)

        assert retrieved_metric is not None
        assert retrieved_metric.id == metric.id
        assert retrieved_metric.name == metric.name
        assert retrieved_metric.experiment_id == test_experiment.id

    async def test_get_by_id_with_string_uuid(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test retrieving a metric by ID using string UUID."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        metric_id_str = str(metric.id)
        retrieved_metric = await metric_repository.get_by_id(metric_id_str)

        assert retrieved_metric is not None
        assert retrieved_metric.id == metric.id
        assert retrieved_metric.name == metric.name

    async def test_get_by_id_not_found(
        self, metric_repository: MetricRepository
    ):
        """Test retrieving a non-existent metric returns None."""
        non_existent_id = uuid4()
        retrieved_metric = await metric_repository.get_by_id(non_existent_id)

        assert retrieved_metric is None

    async def test_update_metric(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test updating a metric using UUID object."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.90,
            step=1,
            direction=MetricDirection.MAXIMIZE,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        updated_metric = await metric_repository.update(
            metric.id,
            name="updated_accuracy",
            value=0.95,
            step=2,
            direction=MetricDirection.MAXIMIZE,
        )

        assert updated_metric.name == "updated_accuracy"
        assert updated_metric.value == 0.95
        assert updated_metric.step == 2
        assert updated_metric.id == metric.id
        assert updated_metric.experiment_id == test_experiment.id

    async def test_update_metric_with_string_uuid(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test updating a metric using string UUID."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.90,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        metric_id_str = str(metric.id)
        updated_metric = await metric_repository.update(
            metric_id_str,
            name="updated_accuracy_string",
            value=0.95,
        )

        assert updated_metric.name == "updated_accuracy_string"
        assert updated_metric.value == 0.95
        assert updated_metric.id == metric.id

    async def test_update_metric_partial_fields(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test updating only some fields of a metric."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.90,
            step=1,
            direction=MetricDirection.MAXIMIZE,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Update only value
        updated_metric = await metric_repository.update(
            metric.id, value=0.95
        )

        assert updated_metric.value == 0.95
        assert updated_metric.name == "accuracy"  # Unchanged
        assert updated_metric.step == 1  # Unchanged
        assert updated_metric.direction == MetricDirection.MAXIMIZE  # Unchanged
        assert updated_metric.id == metric.id

    async def test_update_metric_direction(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test updating a metric's direction."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="loss",
            value=0.05,
            step=1,
            direction=MetricDirection.MINIMIZE,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Update direction
        updated_metric = await metric_repository.update(
            metric.id, direction=MetricDirection.MAXIMIZE
        )

        assert updated_metric.direction == MetricDirection.MAXIMIZE
        assert updated_metric.name == "loss"  # Unchanged
        assert updated_metric.value == 0.05  # Unchanged

    async def test_list_metrics(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test listing all metrics."""
        # Create multiple metrics
        metric1 = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        metric2 = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="loss",
            value=0.05,
            step=1,
        )
        db_session.add_all([metric1, metric2])
        await db_session.flush()
        await db_session.refresh(metric1)
        await db_session.refresh(metric2)

        metrics = await metric_repository.list()

        assert len(metrics) >= 2
        metric_names = [m.name for m in metrics]
        assert "accuracy" in metric_names
        assert "loss" in metric_names

    async def test_list_metrics_with_limit(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test listing metrics with a limit."""
        from lib.db.base_repository import ListOptions

        # Create multiple metrics
        for i in range(5):
            metric = Metric(
                id=None,
                experiment_id=test_experiment.id,
                name=f"metric_{i}",
                value=0.5 + i * 0.1,
                step=i,
            )
            db_session.add(metric)
        await db_session.flush()

        # List with limit
        metrics = await metric_repository.list(ListOptions(limit=3))

        assert len(metrics) <= 3

    async def test_list_metrics_with_offset(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test listing metrics with an offset."""
        from lib.db.base_repository import ListOptions

        # Create multiple metrics
        metric_ids = []
        for i in range(5):
            metric = Metric(
                id=None,
                experiment_id=test_experiment.id,
                name=f"metric_{i}",
                value=0.5 + i * 0.1,
                step=i,
            )
            db_session.add(metric)
            await db_session.flush()
            await db_session.refresh(metric)
            metric_ids.append(metric.id)

        # List with offset
        metrics = await metric_repository.list(ListOptions(limit=2, offset=2))

        assert len(metrics) <= 2

    async def test_delete_metric(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test deleting a metric using string UUID."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Verify metric exists
        retrieved_metric = await metric_repository.get_by_id(metric.id)
        assert retrieved_metric is not None

        # Delete the metric
        metric_id_str = str(metric.id)
        await metric_repository.delete(metric_id_str)

        # Verify metric is deleted
        deleted_metric = await metric_repository.get_by_id(metric.id)
        assert deleted_metric is None

    async def test_delete_metric_with_uuid_object(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test deleting a metric using UUID object."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Verify metric exists
        retrieved_metric = await metric_repository.get_by_id(metric.id)
        assert retrieved_metric is not None

        # Delete using UUID object
        await metric_repository.delete(metric.id)

        # Verify metric is deleted
        deleted_metric = await metric_repository.get_by_id(metric.id)
        assert deleted_metric is None

    async def test_upsert_create_new(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test upsert creating a new metric."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="Upsert Metric",
            value=0.90,
            step=1,
        )

        # First create it normally to get an ID
        created_metric = await metric_repository.create(metric)
        metric_id = created_metric.id

        # Now upsert with same ID should update
        updated_metric = Metric(
            id=metric_id,
            experiment_id=test_experiment.id,
            name="Upserted Metric",
            value=0.95,
            step=2,
        )

        result = await metric_repository.upsert(updated_metric)

        assert result.id == metric_id
        assert result.name == "Upserted Metric"
        assert result.value == 0.95
        assert result.step == 2

    async def test_upsert_update_existing(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test upsert updating an existing metric."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="Original Metric",
            value=0.90,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Modify the metric
        metric.name = "Upserted Name"
        metric.value = 0.95

        result = await metric_repository.upsert(metric)

        assert result.id == metric.id
        assert result.name == "Upserted Name"
        assert result.value == 0.95

    async def test_get_single(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_experiment: Experiment,
    ):
        """Test get_single method (alias for get_by_id)."""
        metric = Metric(
            id=None,
            experiment_id=test_experiment.id,
            name="Test Metric",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        retrieved_metric = await metric_repository.get_single(metric.id)

        assert retrieved_metric is not None
        assert retrieved_metric.id == metric.id
        assert retrieved_metric.name == metric.name

    async def test_get_single_not_found(
        self, metric_repository: MetricRepository
    ):
        """Test get_single returns None for non-existent metric."""
        non_existent_id = uuid4()
        retrieved_metric = await metric_repository.get_single(non_existent_id)

        assert retrieved_metric is None

    # Custom Methods Tests

    async def test_get_metrics_by_experiment_owned_by_user(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting metrics for an experiment owned by the user."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Test Experiment",
            description="Test experiment description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create metrics for the experiment
        metric1 = Metric(
            id=None,
            experiment_id=experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
            direction=MetricDirection.MAXIMIZE,
        )
        metric2 = Metric(
            id=None,
            experiment_id=experiment.id,
            name="loss",
            value=0.05,
            step=1,
            direction=MetricDirection.MINIMIZE,
        )
        db_session.add_all([metric1, metric2])
        await db_session.flush()
        await db_session.refresh(metric1)
        await db_session.refresh(metric2)

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 2
        metric_names = [m.name for m in metrics]
        assert "accuracy" in metric_names
        assert "loss" in metric_names

    async def test_get_metrics_by_experiment_via_team(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting metrics for an experiment accessible via team membership."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team with Experiments",
            description="Team with accessible experiments",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add test_user as member
        member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(member)
        await db_session.flush()

        # Create project in the team
        project = Project(
            id=None,
            name="Team Project",
            description="Project in team",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Team Experiment",
            description="Experiment in team",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create metrics for the experiment
        metric1 = Metric(
            id=None,
            experiment_id=experiment.id,
            name="precision",
            value=0.92,
            step=1,
        )
        metric2 = Metric(
            id=None,
            experiment_id=experiment.id,
            name="recall",
            value=0.88,
            step=1,
        )
        db_session.add_all([metric1, metric2])
        await db_session.flush()
        await db_session.refresh(metric1)
        await db_session.refresh(metric2)

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 2
        metric_names = [m.name for m in metrics]
        assert "precision" in metric_names
        assert "recall" in metric_names

    async def test_get_metrics_by_experiment_not_accessible(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that inaccessible experiment returns empty list."""
        # Create a project owned by test_user_2 with no team
        inaccessible_project = Project(
            id=None,
            name="Inaccessible Project",
            description="Project user cannot access",
            owner_id=test_user_2.id,
            team_id=None,
        )
        db_session.add(inaccessible_project)
        await db_session.flush()
        await db_session.refresh(inaccessible_project)

        # Create experiment in inaccessible project
        inaccessible_experiment = Experiment(
            id=None,
            project_id=inaccessible_project.id,
            name="Inaccessible Experiment",
            description="Experiment user cannot access",
        )
        db_session.add(inaccessible_experiment)
        await db_session.flush()
        await db_session.refresh(inaccessible_experiment)

        # Create metrics for the inaccessible experiment
        metric = Metric(
            id=None,
            experiment_id=inaccessible_experiment.id,
            name="accuracy",
            value=0.90,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()

        # Try to get metrics by experiment (should return empty list)
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, inaccessible_experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 0

    async def test_get_metrics_by_experiment_nonexistent_experiment(
        self,
        metric_repository: MetricRepository,
        test_user: User,
    ):
        """Test getting metrics for non-existent experiment returns empty list."""
        nonexistent_id = uuid4()
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert len(metrics) == 0

    async def test_get_metrics_by_experiment_no_metrics(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting metrics for experiment with no metrics returns empty list."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with No Metrics",
            description="Experiment without metrics",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Get metrics by experiment (should return empty list)
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 0

    async def test_get_metrics_by_experiment_multiple_metrics(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting multiple metrics for an experiment."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with Multiple Metrics",
            description="Experiment with many metrics",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create multiple metrics for the experiment
        metrics_data = [
            ("accuracy", 0.95, 1),
            ("precision", 0.92, 1),
            ("recall", 0.88, 1),
            ("f1_score", 0.90, 1),
        ]
        created_metrics = []
        for name, value, step in metrics_data:
            metric = Metric(
                id=None,
                experiment_id=experiment.id,
                name=name,
                value=value,
                step=step,
            )
            db_session.add(metric)
            created_metrics.append(metric)
        await db_session.flush()
        for metric in created_metrics:
            await db_session.refresh(metric)

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 4
        metric_names = [m.name for m in metrics]
        for name, _, _ in metrics_data:
            assert name in metric_names

    async def test_get_metrics_by_experiment_with_string_uuid(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting metrics using string UUID."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with String UUID",
            description="Testing string UUID",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create a metric for the experiment
        metric = Metric(
            id=None,
            experiment_id=experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Get metrics using string UUID
        experiment_id_str = str(experiment.id)
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment_id_str  # type: ignore[arg-type]
        )

        assert len(metrics) == 1
        assert metrics[0].name == "accuracy"
        assert metrics[0].value == 0.95
        assert metrics[0].experiment_id == experiment.id

    async def test_get_metrics_by_experiment_with_different_steps(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting metrics with different step values."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with Steps",
            description="Experiment with metrics at different steps",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create metrics at different steps
        for step in [1, 10, 20, 30]:
            metric = Metric(
                id=None,
                experiment_id=experiment.id,
                name="loss",
                value=1.0 / step,
                step=step,
            )
            db_session.add(metric)
        await db_session.flush()

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 4
        steps = [m.step for m in metrics]
        assert 1 in steps
        assert 10 in steps
        assert 20 in steps
        assert 30 in steps

    async def test_get_metrics_by_experiment_with_different_directions(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting metrics with different direction values."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with Directions",
            description="Experiment with metrics having different directions",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create metrics with different directions
        metric_minimize = Metric(
            id=None,
            experiment_id=experiment.id,
            name="loss",
            value=0.05,
            step=1,
            direction=MetricDirection.MINIMIZE,
        )
        metric_maximize = Metric(
            id=None,
            experiment_id=experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
            direction=MetricDirection.MAXIMIZE,
        )
        db_session.add_all([metric_minimize, metric_maximize])
        await db_session.flush()
        await db_session.refresh(metric_minimize)
        await db_session.refresh(metric_maximize)

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 2
        directions = [m.direction for m in metrics]
        assert MetricDirection.MINIMIZE in directions
        assert MetricDirection.MAXIMIZE in directions

    async def test_get_metrics_by_experiment_created_at_is_naive_utc(
        self,
        metric_repository: MetricRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that created_at is a naive UTC datetime."""
        # Create a project owned by test_user
        project = Project(
            id=None,
            name="Test Project",
            description="Test project description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Create an experiment in the project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment with Timestamp",
            description="Testing timestamp format",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Create a metric
        metric = Metric(
            id=None,
            experiment_id=experiment.id,
            name="accuracy",
            value=0.95,
            step=1,
        )
        db_session.add(metric)
        await db_session.flush()
        await db_session.refresh(metric)

        # Get metrics by experiment
        metrics = await metric_repository.get_metrics_by_experiment(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert len(metrics) == 1
        assert metrics[0].created_at is not None
        assert isinstance(metrics[0].created_at, datetime)
        assert metrics[0].created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{metrics[0].created_at.tzinfo}"
        )

