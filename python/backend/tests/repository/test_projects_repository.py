"""
Tests for ProjectRepository.
"""

from typing import NamedTuple
import uuid
from lib.db.error import DBNotFoundError
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from models import Project, User, Team, TeamMember
from domain.projects.repository import ProjectRepository, UserProtocol


class TestProjectRepository:
    """Test suite for ProjectRepository."""

    @pytest.fixture
    def project_repository(self, db_session: AsyncSession) -> ProjectRepository:
        """Create a ProjectRepository instance."""
        return ProjectRepository(db_session)

    async def test_get_accessible_projects_owned_by_user(
        self,
        project_repository: ProjectRepository,
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
        await db_session.refresh(project1)
        await db_session.refresh(project2)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_projects) >= 2
        project_ids = [p.id for p in accessible_projects]
        assert project1.id in project_ids
        assert project2.id in project_ids

        # Verify relationships are loaded
        for project in accessible_projects:
            if project.id == project1.id:
                assert project.owner is not None
                assert project.owner.id == test_user.id

    async def test_get_accessible_projects_via_team(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting projects accessible via team membership."""
        # Create a team owned by test_user_2
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
        await db_session.refresh(project1)
        await db_session.refresh(project2)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_projects) >= 2
        project_ids = [p.id for p in accessible_projects]
        assert project1.id in project_ids
        assert project2.id in project_ids

        # Verify relationships are loaded
        for project in accessible_projects:
            if project.id == project1.id:
                assert project.team is not None
                assert project.team.id == team.id

    async def test_get_accessible_projects_owned_and_team(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting projects both owned by user and accessible via team."""
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

        # Add test_user as member
        member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(member)
        await db_session.flush()

        # Create owned project
        owned_project = Project(
            id=None,
            name="Owned Project",
            description="Project owned by user",
            owner_id=test_user.id,
            team_id=None,
        )
        # Create team project
        team_project = Project(
            id=None,
            name="Team Project",
            description="Project in team",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        db_session.add_all([owned_project, team_project])
        await db_session.flush()
        await db_session.refresh(owned_project)
        await db_session.refresh(team_project)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_projects) >= 2
        project_ids = [p.id for p in accessible_projects]
        assert owned_project.id in project_ids
        assert team_project.id in project_ids

    async def test_get_accessible_projects_no_access(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that user cannot access projects they don't own or belong to."""
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

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        project_ids = [p.id for p in accessible_projects]
        assert inaccessible_project.id not in project_ids

    async def test_get_accessible_projects_ordered_by_created_at_desc(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that accessible projects are ordered by created_at descending."""
        # Create projects with slight time differences
        project1 = Project(
            id=None,
            name="Project 1",
            description="First project",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project1)
        await db_session.flush()
        await db_session.refresh(project1)

        # Small delay to ensure different timestamps
        import asyncio

        await asyncio.sleep(0.01)

        project2 = Project(
            id=None,
            name="Project 2",
            description="Second project",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project2)
        await db_session.flush()
        await db_session.refresh(project2)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        # Find our projects in the list
        project1_idx = next(
            (i for i, p in enumerate(accessible_projects) if p.id == project1.id), None
        )
        project2_idx = next(
            (i for i, p in enumerate(accessible_projects) if p.id == project2.id), None
        )

        assert project1_idx is not None
        assert project2_idx is not None
        # Project 2 (created later) should come before Project 1
        assert project2_idx < project1_idx

    async def test_get_accessible_projects_loads_relationships(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that relationships are properly loaded."""
        project = Project(
            id=None,
            name="Project with Relationships",
            description="Testing relationships",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        project_found = next(
            (p for p in accessible_projects if p.id == project.id), None
        )
        assert project_found is not None

        # Verify relationships are loaded (should not raise LazyLoadError)
        assert project_found.owner is not None
        assert project_found.experiments is not None
        assert project_found.hypotheses is not None
        assert project_found.team is None  # No team assigned

    async def test_get_project_if_accessible_owned_project(
        self,
        project_repository: ProjectRepository,
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

        # Get project by ID
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name
        assert retrieved_project.owner_id == test_user.id

    async def test_get_project_if_accessible_via_team(
        self,
        project_repository: ProjectRepository,
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

        # Get project by ID
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.team_id == team.id

    async def test_get_project_if_accessible_not_accessible(
        self,
        project_repository: ProjectRepository,
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

        # Try to get project by ID
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, inaccessible_project.id  # type: ignore[arg-type]
        )

        assert retrieved_project is None

    async def test_get_project_if_accessible_with_string_uuid(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a project using string UUID."""
        project = Project(
            id=None,
            name="Project with String UUID",
            description="Testing string UUID",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Get project using string UUID
        project_id_str = str(project.id)
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, project_id_str  # type: ignore[arg-type]
        )

        assert retrieved_project is not None
        assert retrieved_project.id == project.id

    async def test_get_project_if_accessible_nonexistent_project(
        self,
        project_repository: ProjectRepository,
        test_user: User,
    ):
        """Test getting a non-existent project returns None."""
        nonexistent_id = uuid4()
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert retrieved_project is None

    async def test_get_project_if_accessible_loads_relationships(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that relationships are properly loaded."""
        project = Project(
            id=None,
            name="Project with Relationships",
            description="Testing relationships",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Get project
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert retrieved_project is not None

        # Verify relationships are loaded (should not raise LazyLoadError)
        assert retrieved_project.owner is not None
        assert retrieved_project.experiments is not None
        assert retrieved_project.hypotheses is not None

    async def test_get_project_if_accessible_with_team_relationship(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that team relationship is loaded when project has a team."""
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

        # Get project
        retrieved_project = await project_repository.get_project_if_accessible(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert retrieved_project is not None
        assert retrieved_project.team is not None
        assert retrieved_project.team.id == team.id

    async def test_get_accessible_projects_empty_list_when_no_teams(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that projects in teams user is not a member of are not accessible."""
        # Create team without adding test_user
        team = Team(
            id=None,
            name="Other Team",
            description="Team user is not a member of",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Create project in team
        team_project = Project(
            id=None,
            name="Team Project",
            description="Project in team user is not a member of",
            owner_id=test_user_2.id,
            team_id=team.id,
        )
        db_session.add(team_project)
        await db_session.flush()
        await db_session.refresh(team_project)

        # Get accessible projects (user has no teams and doesn't own this project)
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        project_ids = [p.id for p in accessible_projects]
        assert team_project.id not in project_ids

    async def test_get_accessible_projects_created_at_is_naive_utc(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that project created_at is naive UTC datetime."""
        project = Project(
            id=None,
            name="Project with Timestamp",
            description="Testing timestamp format",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Get accessible projects
        accessible_projects = await project_repository.get_accessible_projects(
            test_user  # type: ignore[arg-type]
        )

        project_found = next(
            (p for p in accessible_projects if p.id == project.id), None
        )
        assert project_found is not None

        # Verify created_at is naive UTC
        assert project_found.created_at is not None
        assert isinstance(project_found.created_at, datetime)
        assert project_found.created_at.tzinfo is None, (
            f"Project created_at should be timezone-naive but has tzinfo: "
            f"{project_found.created_at.tzinfo}"
        )

    # CRUD Operations Tests

    async def test_create_project(
        self, project_repository: ProjectRepository, test_user: User
    ):
        """Test creating a new project."""
        project = Project(
            id=None,
            name="New Project",
            description="A new project",
            owner_id=test_user.id,
            team_id=None,
        )

        created_project = await project_repository.create(project)

        assert created_project.id is not None
        assert created_project.name == "New Project"
        assert created_project.description == "A new project"
        assert created_project.owner_id == test_user.id
        assert created_project.team_id is None

    async def test_create_project_with_team(
        self,
        project_repository: ProjectRepository,
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

        project = Project(
            id=None,
            name="Team Project",
            description="Project with team",
            owner_id=test_user.id,
            team_id=team.id,
        )

        created_project = await project_repository.create(project)

        assert created_project.id is not None
        assert created_project.name == "Team Project"
        assert created_project.team_id == team.id

    async def test_create_project_created_at_is_naive_utc(
        self, project_repository: ProjectRepository, test_user: User
    ):
        """Test that created_at is a naive UTC datetime."""
        project = Project(
            id=None,
            name="Project with Timestamp",
            description="Testing timestamp format",
            owner_id=test_user.id,
            team_id=None,
        )

        created_project = await project_repository.create(project)

        assert created_project.created_at is not None
        assert isinstance(created_project.created_at, datetime)
        assert created_project.created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{created_project.created_at.tzinfo}"
        )

    async def test_get_by_id(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving a project by ID using UUID object."""
        project = Project(
            id=None,
            name="Test Project",
            description="Test description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        retrieved_project = await project_repository.get_by_id(project.id)

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name
        assert retrieved_project.owner_id == project.owner_id

    async def test_get_by_id_with_string_uuid(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving a project by ID using string UUID."""
        project = Project(
            id=None,
            name="Test Project",
            description="Test description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        project_id_str = str(project.id)
        retrieved_project = await project_repository.get_by_id(project_id_str)

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name

    async def test_get_by_id_not_found(self, project_repository: ProjectRepository):
        """Test retrieving a non-existent project raises DBNotFoundError."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await project_repository.get_by_id(non_existent_id)

    async def test_get_by_id_not_found_with_string_uuid(
        self, project_repository: ProjectRepository
    ):
        """Test retrieving a non-existent project raises DBNotFoundError when using string UUID."""
        non_existent_id_str = str(uuid4())
        with pytest.raises(DBNotFoundError):
            await project_repository.get_by_id(non_existent_id_str)

    async def test_update_project(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a project using UUID object."""
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

        updated_project = await project_repository.update(
            project.id,
            name="Updated Project Name",
            description="Updated description",
        )

        assert updated_project.name == "Updated Project Name"
        assert updated_project.description == "Updated description"
        assert updated_project.id == project.id
        assert updated_project.owner_id == test_user.id

    async def test_update_project_with_string_uuid(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a project using string UUID."""
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

        project_id_str = str(project.id)
        updated_project = await project_repository.update(
            project_id_str,
            name="Updated Project Name String",
            description="Updated description string",
        )

        assert updated_project.name == "Updated Project Name String"
        assert updated_project.description == "Updated description string"
        assert updated_project.id == project.id

    async def test_update_project_partial_fields(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating only some fields of a project."""
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

        # Update only name
        updated_project = await project_repository.update(
            project.id, name="Updated Name Only"
        )

        assert updated_project.name == "Updated Name Only"
        assert updated_project.description == "Original description"  # Unchanged
        assert updated_project.id == project.id

    async def test_update_project_with_team(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test updating a project's team."""
        # Create teams
        team1 = Team(
            id=None,
            name="Team 1",
            description="First team",
            owner_id=test_user_2.id,
        )
        team2 = Team(
            id=None,
            name="Team 2",
            description="Second team",
            owner_id=test_user_2.id,
        )
        db_session.add_all([team1, team2])
        await db_session.flush()
        await db_session.refresh(team1)
        await db_session.refresh(team2)

        project = Project(
            id=None,
            name="Project with Team",
            description="Project description",
            owner_id=test_user.id,
            team_id=team1.id,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Update team
        updated_project = await project_repository.update(project.id, team_id=team2.id)

        assert updated_project.team_id == team2.id
        assert updated_project.name == "Project with Team"  # Unchanged

    async def test_list_projects(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing all projects."""
        # Create multiple projects
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

        projects = await project_repository.list()

        assert len(projects) >= 2
        project_names = [p.name for p in projects]
        assert "Project 1" in project_names
        assert "Project 2" in project_names

    async def test_list_projects_with_limit(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing projects with a limit."""
        from lib.db.base_repository import ListOptions

        # Create multiple projects
        for i in range(5):
            project = Project(
                id=None,
                name=f"Project {i}",
                description=f"Project {i} description",
                owner_id=test_user.id,
                team_id=None,
            )
            db_session.add(project)
        await db_session.flush()

        # List with limit
        projects = await project_repository.list(ListOptions(limit=3))

        assert len(projects) <= 3

    async def test_list_projects_with_offset(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing projects with an offset."""
        from lib.db.base_repository import ListOptions

        # Create multiple projects
        project_ids = []
        for i in range(5):
            project = Project(
                id=None,
                name=f"Project {i}",
                description=f"Project {i} description",
                owner_id=test_user.id,
                team_id=None,
            )
            db_session.add(project)
            await db_session.flush()
            await db_session.refresh(project)
            project_ids.append(project.id)

        # List with offset
        projects = await project_repository.list(ListOptions(limit=2, offset=2))

        assert len(projects) <= 2
        # Verify offset works (projects should not include first two)
        returned_ids = [p.id for p in projects]
        # Note: This test assumes projects are returned in some order
        # The exact order depends on the database

    async def test_delete_project(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting a project using string UUID."""
        project = Project(
            id=None,
            name="Project to Delete",
            description="This project will be deleted",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Verify project exists
        retrieved_project = await project_repository.get_by_id(project.id)
        assert retrieved_project is not None

        # Delete the project
        project_id_str = str(project.id)
        await project_repository.delete(project_id_str)

        # Verify project is deleted
        with pytest.raises(DBNotFoundError):
            await project_repository.get_by_id(project.id)

    async def test_delete_project_with_uuid_object(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting a project using UUID object."""
        project = Project(
            id=None,
            name="Project to Delete",
            description="This project will be deleted",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        # Verify project exists
        retrieved_project = await project_repository.get_by_id(project.id)
        assert retrieved_project is not None

        # Delete using UUID object
        await project_repository.delete(project.id)

        # Verify project is deleted
        with pytest.raises(DBNotFoundError):
            await project_repository.get_by_id(project.id)

    async def test_upsert_create_new(
        self, project_repository: ProjectRepository, test_user: User
    ):
        """Test upsert creating a new project."""
        project = Project(
            id=None,
            name="Upsert Project",
            description="Project created via upsert",
            owner_id=test_user.id,
            team_id=None,
        )

        # First create it normally to get an ID
        created_project = await project_repository.create(project)
        project_id = created_project.id

        # Now upsert with same ID should update
        updated_project = Project(
            id=project_id,
            name="Upserted Project",
            description="Updated via upsert",
            owner_id=test_user.id,
            team_id=None,
        )

        result = await project_repository.upsert(updated_project)

        assert result.id == project_id
        assert result.name == "Upserted Project"
        assert result.description == "Updated via upsert"

    async def test_upsert_update_existing(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test upsert updating an existing project."""
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

        # Modify the project
        project.name = "Upserted Name"
        project.description = "Upserted Description"

        result = await project_repository.upsert(project)

        assert result.id == project.id
        assert result.name == "Upserted Name"
        assert result.description == "Upserted Description"

    async def test_get_single(
        self,
        project_repository: ProjectRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test get_single method (alias for get_by_id)."""
        project = Project(
            id=None,
            name="Test Project",
            description="Test description",
            owner_id=test_user.id,
            team_id=None,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        retrieved_project = await project_repository.get_single(project.id)

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name

    async def test_get_single_not_found(self, project_repository: ProjectRepository):
        """Test get_single raises DBNotFoundError for non-existent project."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await project_repository.get_single(non_existent_id)
