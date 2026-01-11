"""
Tests for ExperimentRepository.
"""

import uuid
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from models import Experiment, Project, User, Team, TeamMember, ExperimentStatus
from domain.experiments.repository import ExperimentRepository
from domain.projects.repository import UserProtocol
from lib.db.error import DBNotFoundError


class TestExperimentRepository:
    """Test suite for ExperimentRepository."""

    @pytest.fixture
    def experiment_repository(self, db_session: AsyncSession) -> ExperimentRepository:
        """Create an ExperimentRepository instance."""
        return ExperimentRepository(db_session)

    # CRUD Operations Tests

    async def test_create_experiment(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating a new experiment."""
        # Create a project first
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
            name="New Experiment",
            description="A new experiment",
            status=ExperimentStatus.PLANNED,
        )

        created_experiment = await experiment_repository.create(experiment)

        assert created_experiment.id is not None
        assert created_experiment.name == "New Experiment"
        assert created_experiment.description == "A new experiment"
        assert created_experiment.project_id == project.id
        assert created_experiment.status == ExperimentStatus.PLANNED

    async def test_create_experiment_with_all_fields(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating an experiment with all fields."""
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
            name="Full Experiment",
            description="Experiment with all fields",
            status=ExperimentStatus.RUNNING,
            features={"learning_rate": 0.01, "batch_size": 32},
            progress=50,
            color="#ff0000",
            order=1,
        )

        created_experiment = await experiment_repository.create(experiment)

        assert created_experiment.id is not None
        assert created_experiment.name == "Full Experiment"
        assert created_experiment.status == ExperimentStatus.RUNNING
        assert created_experiment.features == {"learning_rate": 0.01, "batch_size": 32}
        assert created_experiment.progress == 50
        assert created_experiment.color == "#ff0000"
        assert created_experiment.order == 1

    async def test_create_experiment_created_at_is_naive_utc(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that created_at is a naive UTC datetime."""
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
            name="Experiment with Timestamp",
            description="Testing timestamp format",
        )

        created_experiment = await experiment_repository.create(experiment)

        assert created_experiment.created_at is not None
        assert isinstance(created_experiment.created_at, datetime)
        assert created_experiment.created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{created_experiment.created_at.tzinfo}"
        )

    async def test_get_by_id(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving an experiment by ID using UUID object."""
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
            description="Test description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        retrieved_experiment = await experiment_repository.get_by_id(experiment.id)

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id
        assert retrieved_experiment.name == experiment.name
        assert retrieved_experiment.project_id == experiment.project_id

    async def test_get_by_id_with_string_uuid(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving an experiment by ID using string UUID."""
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
            description="Test description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        experiment_id_str = str(experiment.id)
        retrieved_experiment = await experiment_repository.get_by_id(experiment_id_str)

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id
        assert retrieved_experiment.name == experiment.name

    async def test_get_by_id_not_found(
        self, experiment_repository: ExperimentRepository
    ):
        """Test retrieving a non-existent experiment raises DBNotFoundError."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await experiment_repository.get_by_id(non_existent_id)

    async def test_update_experiment(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating an experiment using UUID object."""
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
            name="Original Experiment",
            description="Original description",
            status=ExperimentStatus.PLANNED,
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        updated_experiment = await experiment_repository.update(
            experiment.id,
            name="Updated Experiment Name",
            description="Updated description",
            status=ExperimentStatus.RUNNING,
        )

        assert updated_experiment.name == "Updated Experiment Name"
        assert updated_experiment.description == "Updated description"
        assert updated_experiment.status == ExperimentStatus.RUNNING
        assert updated_experiment.id == experiment.id
        assert updated_experiment.project_id == project.id

    async def test_update_experiment_with_string_uuid(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating an experiment using string UUID."""
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
            name="Original Experiment",
            description="Original description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        experiment_id_str = str(experiment.id)
        updated_experiment = await experiment_repository.update(
            experiment_id_str,
            name="Updated Experiment Name String",
            description="Updated description string",
        )

        assert updated_experiment.name == "Updated Experiment Name String"
        assert updated_experiment.description == "Updated description string"
        assert updated_experiment.id == experiment.id

    async def test_update_experiment_partial_fields(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating only some fields of an experiment."""
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
            name="Original Experiment",
            description="Original description",
            status=ExperimentStatus.PLANNED,
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Update only name
        updated_experiment = await experiment_repository.update(
            experiment.id, name="Updated Name Only"
        )

        assert updated_experiment.name == "Updated Name Only"
        assert updated_experiment.description == "Original description"  # Unchanged
        assert updated_experiment.status == ExperimentStatus.PLANNED  # Unchanged
        assert updated_experiment.id == experiment.id

    async def test_update_experiment_features(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating an experiment's features."""
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
            name="Experiment with Features",
            features={"learning_rate": 0.01},
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Update features
        updated_features = {"learning_rate": 0.02, "batch_size": 64}
        updated_experiment = await experiment_repository.update(
            experiment.id, features=updated_features
        )

        assert updated_experiment.features == updated_features
        assert updated_experiment.name == "Experiment with Features"  # Unchanged

    async def test_list_experiments(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing all experiments."""
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

        # Create multiple experiments
        experiment1 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 1",
            description="First experiment",
        )
        experiment2 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 2",
            description="Second experiment",
        )
        db_session.add_all([experiment1, experiment2])
        await db_session.flush()
        await db_session.refresh(experiment1)
        await db_session.refresh(experiment2)

        experiments = await experiment_repository.list()

        assert len(experiments) >= 2
        experiment_names = [e.name for e in experiments]
        assert "Experiment 1" in experiment_names
        assert "Experiment 2" in experiment_names

    async def test_list_experiments_with_limit(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing experiments with a limit."""
        from lib.db.base_repository import ListOptions

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

        # Create multiple experiments
        for i in range(5):
            experiment = Experiment(
                id=None,
                project_id=project.id,
                name=f"Experiment {i}",
                description=f"Experiment {i} description",
            )
            db_session.add(experiment)
        await db_session.flush()

        # List with limit
        experiments = await experiment_repository.list(ListOptions(limit=3))

        assert len(experiments) <= 3

    async def test_list_experiments_with_offset(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing experiments with an offset."""
        from lib.db.base_repository import ListOptions

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

        # Create multiple experiments
        experiment_ids = []
        for i in range(5):
            experiment = Experiment(
                id=None,
                project_id=project.id,
                name=f"Experiment {i}",
                description=f"Experiment {i} description",
            )
            db_session.add(experiment)
            await db_session.flush()
            await db_session.refresh(experiment)
            experiment_ids.append(experiment.id)

        # List with offset
        experiments = await experiment_repository.list(ListOptions(limit=2, offset=2))

        assert len(experiments) <= 2

    async def test_delete_experiment(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an experiment using string UUID."""
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
            name="Experiment to Delete",
            description="This experiment will be deleted",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Verify experiment exists
        retrieved_experiment = await experiment_repository.get_by_id(experiment.id)
        assert retrieved_experiment is not None

        # Delete the experiment
        experiment_id_str = str(experiment.id)
        await experiment_repository.delete(experiment_id_str)

        # Verify experiment is deleted
        with pytest.raises(DBNotFoundError):
            await experiment_repository.get_by_id(experiment.id)

    async def test_delete_experiment_with_uuid_object(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an experiment using UUID object."""
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
            name="Experiment to Delete",
            description="This experiment will be deleted",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Verify experiment exists
        retrieved_experiment = await experiment_repository.get_by_id(experiment.id)
        assert retrieved_experiment is not None

        # Delete using UUID object
        await experiment_repository.delete(experiment.id)

        # Verify experiment is deleted
        with pytest.raises(DBNotFoundError):
            await experiment_repository.get_by_id(experiment.id)

    async def test_upsert_create_new(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test upsert creating a new experiment."""
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
            name="Upsert Experiment",
            description="Experiment created via upsert",
        )

        # First create it normally to get an ID
        created_experiment = await experiment_repository.create(experiment)
        experiment_id = created_experiment.id

        # Now upsert with same ID should update
        updated_experiment = Experiment(
            id=experiment_id,
            project_id=project.id,
            name="Upserted Experiment",
            description="Updated via upsert",
        )

        result = await experiment_repository.upsert(updated_experiment)

        assert result.id == experiment_id
        assert result.name == "Upserted Experiment"
        assert result.description == "Updated via upsert"

    async def test_upsert_update_existing(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test upsert updating an existing experiment."""
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
            name="Original Experiment",
            description="Original description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Modify the experiment
        experiment.name = "Upserted Name"
        experiment.description = "Upserted Description"

        result = await experiment_repository.upsert(experiment)

        assert result.id == experiment.id
        assert result.name == "Upserted Name"
        assert result.description == "Upserted Description"

    async def test_get_single(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test get_single method (alias for get_by_id)."""
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
            description="Test description",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        retrieved_experiment = await experiment_repository.get_single(experiment.id)

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id
        assert retrieved_experiment.name == experiment.name

    async def test_get_single_not_found(
        self, experiment_repository: ExperimentRepository
    ):
        """Test get_single raises DBNotFoundError for non-existent experiment."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await experiment_repository.get_single(non_existent_id)

    # Custom Methods Tests

    async def test_get_accessible_experiments_owned_by_user(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting experiments owned by the user."""
        # Create projects owned by test_user
        project1 = Project(
            id=None,
            name="Project 1",
            description="First project",
            owner_id=test_user.id,
            team_id=None,
        )
        project2 = Project(
            id=None,
            name="Project 2",
            description="Second project",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add_all([project1, project2])
        await db_session.flush()
        await db_session.refresh(project1)
        await db_session.refresh(project2)

        # Create experiments in these projects
        experiment1 = Experiment(
            id=None,
            project_id=project1.id,
            name="Experiment 1",
            description="First experiment",
        )
        experiment2 = Experiment(
            id=None,
            project_id=project2.id,
            name="Experiment 2",
            description="Second experiment",
        )
        db_session.add_all([experiment1, experiment2])
        await db_session.flush()
        await db_session.refresh(experiment1)
        await db_session.refresh(experiment2)

        # Get accessible experiments
        accessible_experiments = await experiment_repository.get_accessible_experiments(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_experiments) >= 2
        experiment_ids = [e.id for e in accessible_experiments]
        assert experiment1.id in experiment_ids
        assert experiment2.id in experiment_ids

    async def test_get_accessible_experiments_via_team(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting experiments accessible via team membership."""
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

        # Create experiments in the project
        experiment1 = Experiment(
            id=None,
            project_id=project.id,
            name="Team Experiment 1",
            description="First team experiment",
        )
        experiment2 = Experiment(
            id=None,
            project_id=project.id,
            name="Team Experiment 2",
            description="Second team experiment",
        )
        db_session.add_all([experiment1, experiment2])
        await db_session.flush()
        await db_session.refresh(experiment1)
        await db_session.refresh(experiment2)

        # Get accessible experiments
        accessible_experiments = await experiment_repository.get_accessible_experiments(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_experiments) >= 2
        experiment_ids = [e.id for e in accessible_experiments]
        assert experiment1.id in experiment_ids
        assert experiment2.id in experiment_ids

    async def test_get_accessible_experiments_ordered_by_created_at_desc(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that accessible experiments are ordered by created_at descending."""
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

        # Create experiments with slight time differences
        experiment1 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 1",
            description="First experiment",
        )
        db_session.add(experiment1)
        await db_session.flush()
        await db_session.refresh(experiment1)

        # Small delay to ensure different timestamps
        import asyncio

        await asyncio.sleep(0.01)

        experiment2 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 2",
            description="Second experiment",
        )
        db_session.add(experiment2)
        await db_session.flush()
        await db_session.refresh(experiment2)

        # Get accessible experiments
        accessible_experiments = await experiment_repository.get_accessible_experiments(
            test_user  # type: ignore[arg-type]
        )

        # Find our experiments in the list
        experiment1_idx = next(
            (i for i, e in enumerate(accessible_experiments) if e.id == experiment1.id),
            None,
        )
        experiment2_idx = next(
            (i for i, e in enumerate(accessible_experiments) if e.id == experiment2.id),
            None,
        )

        assert experiment1_idx is not None
        assert experiment2_idx is not None
        # Experiment 2 (created later) should come before Experiment 1
        assert experiment2_idx < experiment1_idx

    async def test_get_accessible_experiments_no_access(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that user cannot access experiments they don't own or belong to."""
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

        # Get accessible experiments
        accessible_experiments = await experiment_repository.get_accessible_experiments(
            test_user  # type: ignore[arg-type]
        )

        experiment_ids = [e.id for e in accessible_experiments]
        assert inaccessible_experiment.id not in experiment_ids

    async def test_get_experiments_by_project(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting experiments by project ID."""
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

        # Create experiments in the project
        experiment1 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 1",
            description="First experiment",
            order=1,
        )
        experiment2 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 2",
            description="Second experiment",
            order=2,
        )
        db_session.add_all([experiment1, experiment2])
        await db_session.flush()
        await db_session.refresh(experiment1)
        await db_session.refresh(experiment2)

        # Get experiments by project
        experiments = await experiment_repository.get_experiments_by_project(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert len(experiments) == 2
        experiment_ids = [e.id for e in experiments]
        assert experiment1.id in experiment_ids
        assert experiment2.id in experiment_ids

    async def test_get_experiments_by_project_ordered_by_order(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that experiments are ordered by order field."""
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

        # Create experiments with different order values
        experiment1 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 1",
            order=2,
        )
        experiment2 = Experiment(
            id=None,
            project_id=project.id,
            name="Experiment 2",
            order=1,
        )
        db_session.add_all([experiment1, experiment2])
        await db_session.flush()
        await db_session.refresh(experiment1)
        await db_session.refresh(experiment2)

        # Get experiments by project
        experiments = await experiment_repository.get_experiments_by_project(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert len(experiments) == 2
        # Experiment 2 (order=1) should come before Experiment 1 (order=2)
        assert experiments[0].order <= experiments[1].order
        assert experiments[0].id == experiment2.id
        assert experiments[1].id == experiment1.id

    async def test_get_experiments_by_project_inaccessible_project(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that inaccessible project returns empty list."""
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
        experiment = Experiment(
            id=None,
            project_id=inaccessible_project.id,
            name="Experiment",
            description="Experiment in inaccessible project",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Get experiments by project (should return empty list)
        experiments = await experiment_repository.get_experiments_by_project(
            test_user, inaccessible_project.id  # type: ignore[arg-type]
        )

        assert len(experiments) == 0

    async def test_get_experiments_by_project_nonexistent_project(
        self,
        experiment_repository: ExperimentRepository,
        test_user: User,
    ):
        """Test getting experiments for non-existent project returns empty list."""
        nonexistent_id = uuid4()
        experiments = await experiment_repository.get_experiments_by_project(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert len(experiments) == 0

    async def test_get_experiment_if_accessible_owned_project(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting an experiment that user owns."""
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
            name="Owned Experiment",
            description="Experiment owned by user",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Get experiment by ID
        retrieved_experiment = await experiment_repository.get_experiment_if_accessible(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id
        assert retrieved_experiment.name == experiment.name
        assert retrieved_experiment.project_id == project.id

    async def test_get_experiment_if_accessible_via_team(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting an experiment accessible via team membership."""
        # Create team
        team = Team(
            id=None,
            name="Test Team",
            description="Test team",
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

        # Create project in team
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

        # Create experiment in project
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name="Team Experiment",
            description="Experiment in team",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Get experiment by ID
        retrieved_experiment = await experiment_repository.get_experiment_if_accessible(
            test_user, experiment.id  # type: ignore[arg-type]
        )

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id
        assert retrieved_experiment.project_id == project.id

    async def test_get_experiment_if_accessible_not_accessible(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that inaccessible experiment returns None."""
        # Create project owned by test_user_2 with no team
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

        # Try to get experiment by ID
        retrieved_experiment = await experiment_repository.get_experiment_if_accessible(
            test_user, inaccessible_experiment.id  # type: ignore[arg-type]
        )

        assert retrieved_experiment is None

    async def test_get_experiment_if_accessible_with_string_uuid(
        self,
        experiment_repository: ExperimentRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting an experiment using string UUID."""
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
            name="Experiment with String UUID",
            description="Testing string UUID",
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)

        # Get experiment using string UUID
        experiment_id_str = str(experiment.id)
        retrieved_experiment = await experiment_repository.get_experiment_if_accessible(
            test_user, experiment_id_str  # type: ignore[arg-type]
        )

        assert retrieved_experiment is not None
        assert retrieved_experiment.id == experiment.id

    async def test_get_experiment_if_accessible_nonexistent_experiment(
        self,
        experiment_repository: ExperimentRepository,
        test_user: User,
    ):
        """Test getting a non-existent experiment returns None."""
        nonexistent_id = uuid4()
        retrieved_experiment = await experiment_repository.get_experiment_if_accessible(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert retrieved_experiment is None
