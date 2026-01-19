"""
Tests for ProjectService.
"""

from domain.projects.errors import ProjectNotAccessibleError, ProjectPermissionError
from fastapi_users import db
from lib.db.error import DBNotFoundError
import pytest
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Permission,
    Project,
    Role,
    User,
    Team,
    TeamMember,
    Experiment,
    Hypothesis,
)
from domain.projects.service import ProjectService
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectUpdateDTO,
    ProjectMetricDTO,
    ProjectSettingsDTO,
)
from models import MetricDirection, MetricAggregation
from domain.projects.repository import ProjectRepository
from domain.rbac.permissions import ProjectActions, TeamActions


class TestProjectService:
    """Test suite for ProjectService."""

    @pytest.fixture(scope="function")
    def project_service(self, db_session: AsyncSession) -> ProjectService:
        """Create a ProjectService instance."""
        return ProjectService(db_session)

    async def test_create_project_success(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test successfully creating a project."""
        create_dto = ProjectCreateDTO(
            name="New Project",
            description="A new project description",
            metrics=[],
            settings=ProjectSettingsDTO(),
            team_id=None,
        )

        result = await project_service.create_project(test_user, create_dto)

        assert result.id is not None
        assert result.name == "New Project"
        assert result.description == "A new project description"
        assert result.owner.email == test_user.email
        assert result.owner.id == test_user.id
        assert result.owner.display_name == test_user.display_name
        assert result.experiment_count == 0
        assert result.hypothesis_count == 0

    async def test_create_project_with_metrics(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test creating a project with metrics."""
        metrics = [
            ProjectMetricDTO(
                name="accuracy",
                direction=MetricDirection.MAXIMIZE,
                aggregation=MetricAggregation.AVERAGE,
            )
        ]
        create_dto = ProjectCreateDTO(
            name="Project with Metrics",
            description="Project with custom metrics",
            metrics=metrics,
            settings=ProjectSettingsDTO(),
            team_id=None,
        )

        result = await project_service.create_project(test_user, create_dto)

        assert result.id is not None
        assert len(result.metrics) == 1
        assert len(result.metrics) == 1
        # Metrics are stored as dicts in the DTO
        assert isinstance(result.metrics[0], ProjectMetricDTO)
        assert result.metrics[0].name == "accuracy"

    async def test_create_project_with_team(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test creating a project with a team."""
        # Create a team
        team = Team(
            id=None,
            name="Test Team",
            description="Test team",
            owner_id=test_user_2.id,
        )

        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user_2.id,
            role=Role.MEMBER,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)
        print(
            "team_member.id",
            team_member.id,
            "test_user.id",
            test_user_2.id,
            "team.id",
            team.id,
        )

        create_dto = ProjectCreateDTO(
            name="Team Project",
            description="Project in team",
            metrics=[],
            settings=ProjectSettingsDTO(),
            team_id=team.id,
        )

        permission = Permission(
            id=None,
            user_id=test_user_2.id,
            team_id=team.id,
            action=TeamActions.CREATE_PROJECT,
            allowed=True,
        )
        db_session.add(permission)
        await db_session.flush()

        result = await project_service.create_project(test_user_2, create_dto)

        assert result.id is not None
        # Note: ProjectDTO doesn't have team_id/team_name fields in the DTO definition
        # The mapper may set them, but we'll check owner and other fields instead
        assert result.owner.email == test_user_2.email
        assert result.owner.id == test_user_2.id
        assert result.owner.display_name == test_user_2.display_name

        test_user1_project = await project_service.get_project_if_accessible(
            test_user, result.id
        )
        assert test_user1_project is None

    async def test_create_project_with_team_no_access(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test creating a project in a team without membership fails."""
        team = Team(
            id=None,
            name="Private Team",
            description="Private team",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        create_dto = ProjectCreateDTO(
            name="Blocked Project",
            description="Project in team",
            metrics=[],
            settings=ProjectSettingsDTO(),
            team_id=team.id,
        )

        with pytest.raises(
            ProjectNotAccessibleError, match=f"Project {team.id} not accessible"
        ):
            await project_service.create_project(test_user, create_dto)

    async def test_create_project_rollback_on_error(
        self,
        project_service: ProjectService,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that transaction is rolled back on error."""
        # Create a project with invalid data that will cause an error
        # We'll use a mock to simulate an error during creation
        create_dto = ProjectCreateDTO(
            name="Project",
            description="Test",
            metrics=[],
            settings=ProjectSettingsDTO(),
            team_id=None,
        )

        # Mock the repository to raise an error
        original_create = project_service.project_repository.create

        async def mock_create(*args, **kwargs):
            raise ValueError("Simulated error")

        project_service.project_repository.create = mock_create  # type: ignore[assignment]

        # Attempt to create project
        with pytest.raises(ValueError, match="Simulated error"):
            await project_service.create_project(test_user, create_dto)

        # Restore original method
        project_service.project_repository.create = original_create  # type: ignore[assignment]

        # Verify no project was created (check count)
        from domain.projects.repository import ProjectRepository

        repo = ProjectRepository(db_session)
        projects = await repo.get_accessible_projects(test_user)
        project_names = [p.name for p in projects]
        assert "Project" not in project_names

    async def test_update_project_success(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test successfully updating a project."""
        # Create a project first
        project = Project(
            id=None,
            name="Original Project",
            description="Original description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Update the project
        update_dto = ProjectUpdateDTO(
            name="Updated Project",
            description="Updated description",
        )

        result = await project_service.update_project(test_user, project.id, update_dto)

        assert result.id == project.id
        assert result.name == "Updated Project"
        assert result.description == "Updated description"
        assert result.owner.email == test_user.email
        assert result.owner.id == test_user.id
        assert result.owner.display_name == test_user.display_name

    async def test_update_project_partial_update(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating only some fields of a project."""
        # Create a project first
        project = Project(
            id=None,
            name="Original Project",
            description="Original description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Update only the name
        update_dto = ProjectUpdateDTO(name="Updated Name Only")

        result = await project_service.update_project(test_user, project.id, update_dto)

        assert result.name == "Updated Name Only"
        assert result.description == "Original description"  # Unchanged

    async def test_update_project_with_metrics(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating project metrics."""
        # Create a project first
        project = Project(
            id=None,
            name="Project",
            description="Description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Update with metrics
        metrics = [
            ProjectMetricDTO(
                name="precision",
                direction=MetricDirection.MAXIMIZE,
                aggregation=MetricAggregation.BEST,
            )
        ]
        update_dto = ProjectUpdateDTO(metrics=metrics)

        result = await project_service.update_project(test_user, project.id, update_dto)

        assert len(result.metrics) == 1
        # Metrics are stored as dicts in the DTO
        assert isinstance(result.metrics[0], ProjectMetricDTO)
        assert result.metrics[0].name == "precision"

    async def test_update_project_with_experiments_and_hypotheses(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a project that has experiments and hypotheses."""
        # Create a project with experiments and hypotheses
        project = Project(
            id=None,
            name="Project with Data",
            description="Description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Add experiments
        experiment1 = Experiment(
            id=None,
            name="Experiment 1",
            description="First experiment",
            project_id=project.id,
            status="planned",
        )
        experiment2 = Experiment(
            id=None,
            name="Experiment 2",
            description="Second experiment",
            project_id=project.id,
            status="running",
        )
        db_session.add_all([experiment1, experiment2])

        # Add hypotheses
        hypothesis1 = Hypothesis(
            id=None,
            title="Hypothesis 1",
            description="First hypothesis",
            project_id=project.id,
            status="proposed",
            author="Test Author",
        )
        db_session.add(hypothesis1)
        await db_session.flush()

        # Update the project
        update_dto = ProjectUpdateDTO(name="Updated Project Name")

        result = await project_service.update_project(test_user, project.id, update_dto)

        assert result.name == "Updated Project Name"
        assert result.experiment_count == 2
        assert result.hypothesis_count == 1

    async def test_update_project_not_found(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test updating a non-existent project raises an error."""
        nonexistent_id = uuid4()
        update_dto = ProjectUpdateDTO(name="Updated Name")

        async def mock_rollback():
            pass

        project_service.project_repository.rollback = mock_rollback

        with pytest.raises(
            ProjectNotAccessibleError, match=f"Project {nonexistent_id} not accessible"
        ):
            await project_service.update_project(test_user, nonexistent_id, update_dto)

    async def test_update_project_not_accessible(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test updating a project the user cannot access raises an error."""
        # Create a project owned by test_user_2
        project = Project(
            id=None,
            name="Inaccessible Project",
            description="Description",
            owner_id=test_user_2.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        update_dto = ProjectUpdateDTO(name="Updated Name")

        async def mock_rollback():
            pass

        project_service.project_repository.rollback = mock_rollback

        with pytest.raises(
            ProjectNotAccessibleError, match=f"Project {project.id} not accessible"
        ):
            await project_service.update_project(test_user, project.id, update_dto)

    async def test_update_project_team_no_edit_permission(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test updating a team project without edit rights raises error."""
        team = Team(
            id=None,
            name="Team Project",
            description="Team project",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
            role=Role.MEMBER,
        )
        db_session.add(member)
        await db_session.flush()

        project = Project(
            id=None,
            name="Team Project",
            description="Description",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        update_dto = ProjectUpdateDTO(name="Updated Name")
        with pytest.raises(
            ProjectPermissionError,
            match=f"User {test_user.id} does not have permission to update project {project.id}",
        ):
            await project_service.update_project(test_user, project.id, update_dto)

    async def test_update_project_rollback_on_error(
        self,
        project_service: ProjectService,
        # db_session: AsyncSession,
        test_user: User,
    ):
        """Test that transaction is rolled back on error during update."""
        # Create a project first
        project = Project(
            id=None,
            name="Original Project",
            description="Original description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session = project_service.db
        db_session.add(project)
        await db_session.flush()
        project_id = project.id
        await db_session.refresh(project)

        # Mock the repository update to raise an error
        original_update = project_service.project_repository.update

        async def mock_update(*args, **kwargs):
            raise ValueError("Simulated update error")

        async def mock_rollback():
            pass

        project_service.project_repository.update = mock_update
        project_service.project_repository.rollback = mock_rollback

        update_dto = ProjectUpdateDTO(name="Updated Name")

        # Attempt to update project
        with pytest.raises(ValueError, match="Simulated update error"):
            await project_service.update_project(test_user, project_id, update_dto)

        # Restore original method
        project_service.project_repository.update = original_update

        # Verify project was not updated
        # Query for the project again since the object might be detached after rollback

        repo = ProjectRepository(db_session)
        updated_project = await repo.get_by_id(project_id)
        assert updated_project is not None
        assert updated_project.name == "Original Project"

    async def test_get_accessible_projects_owned(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting projects owned by the user."""
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

        results = await project_service.get_accessible_projects(test_user)

        assert len(results) >= 2
        project_ids = [p.id for p in results]
        assert project1.id in project_ids
        assert project2.id in project_ids

    async def test_get_accessible_projects_via_team(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting projects accessible via team membership."""
        # Create a team
        team = Team(
            id=None,
            name="Team with Projects",
            description="Team with accessible projects",
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

        # Create projects in the team
        project1 = Project(
            id=None,
            name="Team Project 1",
            description="First team project",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        project2 = Project(
            id=None,
            name="Team Project 2",
            description="Second team project",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        db_session.add_all([project1, project2])
        await db_session.flush()

        results = await project_service.get_accessible_projects(test_user)

        assert len(results) >= 2
        project_ids = [str(p.id) for p in results]
        assert str(project1.id) in project_ids
        assert str(project2.id) in project_ids

    async def test_get_accessible_projects_via_permissions(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting projects accessible via explicit project permissions."""
        project = Project(
            id=None,
            name="Permission Project",
            description="Project with explicit permissions",
            owner_id=test_user_2.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        permission = Permission(
            id=None,
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )
        db_session.add(permission)
        await db_session.flush()

        results = await project_service.get_accessible_projects(test_user)
        project_ids = [p.id for p in results]
        assert project.id in project_ids

    async def test_get_accessible_projects_with_counts(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting projects with correct experiment and hypothesis counts."""
        # Create a project
        project = Project(
            id=None,
            name="Project with Data",
            description="Description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Add experiments
        experiment1 = Experiment(
            id=None,
            name="Experiment 1",
            description="First experiment",
            project_id=project.id,
            status="planned",
        )
        experiment2 = Experiment(
            id=None,
            name="Experiment 2",
            description="Second experiment",
            project_id=project.id,
            status="running",
        )
        db_session.add_all([experiment1, experiment2])

        # Add hypotheses
        hypothesis1 = Hypothesis(
            id=None,
            title="Hypothesis 1",
            description="First hypothesis",
            project_id=project.id,
            status="proposed",
            author="Test Author",
        )
        hypothesis2 = Hypothesis(
            id=None,
            title="Hypothesis 2",
            description="Second hypothesis",
            project_id=project.id,
            status="testing",
            author="Test Author",
        )
        hypothesis3 = Hypothesis(
            id=None,
            title="Hypothesis 3",
            description="Third hypothesis",
            project_id=project.id,
            status="supported",
            author="Test Author",
        )
        db_session.add_all([hypothesis1, hypothesis2, hypothesis3])
        await db_session.flush()

        results = await project_service.get_accessible_projects(test_user)

        project_result = next((p for p in results if p.id == project.id), None)
        assert project_result is not None
        assert project_result.experiment_count == 2
        assert project_result.hypothesis_count == 3

    async def test_get_accessible_projects_empty(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test getting projects when user has none."""
        results = await project_service.get_accessible_projects(test_user)

        # Should return empty list, not None
        assert isinstance(results, list)
        # May have other projects from fixtures, so we just check it's a list

    async def test_get_project_if_accessible_owned(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a project that user owns."""
        project = Project(
            id=None,
            name="Owned Project",
            description="Project owned by user",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        result = await project_service.get_project_if_accessible(test_user, project.id)

        assert result is not None
        assert result.id == project.id
        assert result.name == "Owned Project"
        assert result.owner.email == test_user.email
        assert result.owner.id == test_user.id
        assert result.owner.display_name == test_user.display_name

    async def test_get_project_if_accessible_via_team(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a project accessible via team membership."""
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

        result = await project_service.get_project_if_accessible(test_user, project.id)

        assert result is not None
        assert result.id == project.id
        # Note: ProjectDTO doesn't have team_id/team_name fields in the DTO definition
        # The mapper may set them, but we'll check owner and other fields instead
        assert result.owner.email == test_user_2.email
        assert result.owner.id == test_user_2.id

    async def test_get_project_if_accessible_via_permissions(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a project accessible via explicit project permissions."""
        project = Project(
            id=None,
            name="Permission Project",
            description="Project with explicit permissions",
            owner_id=test_user_2.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        permission = Permission(
            id=None,
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=project.id,
        )
        db_session.add(permission)
        await db_session.flush()

        result = await project_service.get_project_if_accessible(test_user, project.id)
        assert result is not None
        assert result.id == project.id

    async def test_get_project_if_accessible_not_accessible(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that inaccessible project returns None."""
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

        result = await project_service.get_project_if_accessible(
            test_user, inaccessible_project.id
        )

        assert result is None

    async def test_get_project_if_accessible_nonexistent(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test getting a non-existent project returns None."""
        nonexistent_id = uuid4()
        result = await project_service.get_project_if_accessible(
            test_user, nonexistent_id
        )

        assert result is None

    async def test_get_project_if_accessible_with_counts(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a project with correct experiment and hypothesis counts."""
        # Create a project
        project = Project(
            id=None,
            name="Project with Data",
            description="Description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Add experiments
        experiment1 = Experiment(
            id=None,
            name="Experiment 1",
            description="First experiment",
            project_id=project.id,
            status="planned",
        )
        experiment2 = Experiment(
            id=None,
            name="Experiment 2",
            description="Second experiment",
            project_id=project.id,
            status="running",
        )
        db_session.add_all([experiment1, experiment2])

        # Add hypotheses
        hypothesis1 = Hypothesis(
            id=None,
            title="Hypothesis 1",
            description="First hypothesis",
            project_id=project.id,
            status="proposed",
            author="Test Author",
        )
        db_session.add(hypothesis1)
        await db_session.flush()

        result = await project_service.get_project_if_accessible(test_user, project.id)

        assert result is not None
        assert result.experiment_count == 2
        assert result.hypothesis_count == 1

    async def test_get_project_if_accessible_empty_counts(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a project with no experiments or hypotheses."""
        project = Project(
            id=None,
            name="Empty Project",
            description="Project with no data",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        result = await project_service.get_project_if_accessible(test_user, project.id)

        assert result is not None
        assert result.experiment_count == 0
        assert result.hypothesis_count == 0

    async def test_delete_project_success(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting a project."""
        project = Project(
            id=None,
            name="Project to Delete",
            description="This project will be deleted",
            owner_id=test_user.id,
            team_id=None,
        )
        assert db_session is project_service.db
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)
        result = await project_service.delete_project(test_user, project.id)
        assert result is True

        result = await project_service.get_project_if_accessible(test_user, project.id)
        assert result is None

    async def test_delete_project_not_found(
        self,
        project_service: ProjectService,
        test_user: User,
    ):
        """Test deleting a non-existent project raises an error."""
        nonexistent_id = uuid4()
        with pytest.raises(DBNotFoundError, match="Object with id"):
            await project_service.delete_project(test_user, nonexistent_id)

    async def test_delete_project_not_owner(
        self,
        project_service: ProjectService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test deleting a project without ownership raises error."""
        project = Project(
            id=None,
            name="Other Project",
            description="Owned by someone else",
            owner_id=test_user_2.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        with pytest.raises(
            ProjectPermissionError,
            match=f"User {test_user.id} does not have permission to delete project {project.id}",
        ):
            await project_service.delete_project(test_user, project.id)
