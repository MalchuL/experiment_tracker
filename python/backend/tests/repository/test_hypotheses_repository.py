"""
Tests for HypothesisRepository.
"""

import uuid
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from models import Hypothesis, Project, User, Team, TeamMember, HypothesisStatus
from domain.hypotheses.repository import HypothesisRepository
from domain.projects.repository import UserProtocol
from lib.db.error import DBNotFoundError


class TestHypothesisRepository:
    """Test suite for HypothesisRepository."""

    @pytest.fixture
    def hypothesis_repository(self, db_session: AsyncSession) -> HypothesisRepository:
        """Create a HypothesisRepository instance."""
        return HypothesisRepository(db_session)

    # CRUD Operations Tests

    async def test_create_hypothesis(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating a new hypothesis."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="New Hypothesis",
            description="A new hypothesis",
            author="Test Author",
            status=HypothesisStatus.PROPOSED,
        )

        created_hypothesis = await hypothesis_repository.create(hypothesis)

        assert created_hypothesis.id is not None
        assert created_hypothesis.title == "New Hypothesis"
        assert created_hypothesis.description == "A new hypothesis"
        assert created_hypothesis.project_id == project.id
        assert created_hypothesis.author == "Test Author"
        assert created_hypothesis.status == HypothesisStatus.PROPOSED

    async def test_create_hypothesis_with_all_fields(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating a hypothesis with all fields."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Full Hypothesis",
            description="Hypothesis with all fields",
            author="Test Author",
            status=HypothesisStatus.TESTING,
            target_metrics=["accuracy", "precision"],
            baseline="experiment_123",
        )

        created_hypothesis = await hypothesis_repository.create(hypothesis)

        assert created_hypothesis.id is not None
        assert created_hypothesis.title == "Full Hypothesis"
        assert created_hypothesis.status == HypothesisStatus.TESTING
        assert created_hypothesis.target_metrics == ["accuracy", "precision"]
        assert created_hypothesis.baseline == "experiment_123"

    async def test_create_hypothesis_created_at_is_naive_utc(
        self,
        hypothesis_repository: HypothesisRepository,
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis with Timestamp",
            description="Testing timestamp format",
            author="Test Author",
        )

        created_hypothesis = await hypothesis_repository.create(hypothesis)

        assert created_hypothesis.created_at is not None
        assert isinstance(created_hypothesis.created_at, datetime)
        assert created_hypothesis.created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{created_hypothesis.created_at.tzinfo}"
        )

    async def test_get_by_id(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving a hypothesis by ID using UUID object."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Test Hypothesis",
            description="Test description",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        retrieved_hypothesis = await hypothesis_repository.get_by_id(hypothesis.id)

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id
        assert retrieved_hypothesis.title == hypothesis.title
        assert retrieved_hypothesis.project_id == hypothesis.project_id

    async def test_get_by_id_with_string_uuid(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test retrieving a hypothesis by ID using string UUID."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Test Hypothesis",
            description="Test description",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        hypothesis_id_str = str(hypothesis.id)
        retrieved_hypothesis = await hypothesis_repository.get_by_id(hypothesis_id_str)

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id
        assert retrieved_hypothesis.title == hypothesis.title

    async def test_get_by_id_not_found(
        self, hypothesis_repository: HypothesisRepository
    ):
        """Test retrieving a non-existent hypothesis raises DBNotFoundError."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await hypothesis_repository.get_by_id(non_existent_id)

    async def test_update_hypothesis(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a hypothesis using UUID object."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Original Hypothesis",
            description="Original description",
            author="Original Author",
            status=HypothesisStatus.PROPOSED,
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        updated_hypothesis = await hypothesis_repository.update(
            hypothesis.id,
            title="Updated Hypothesis Title",
            description="Updated description",
            status=HypothesisStatus.TESTING,
        )

        assert updated_hypothesis.title == "Updated Hypothesis Title"
        assert updated_hypothesis.description == "Updated description"
        assert updated_hypothesis.status == HypothesisStatus.TESTING
        assert updated_hypothesis.id == hypothesis.id
        assert updated_hypothesis.project_id == project.id
        assert updated_hypothesis.author == "Original Author"  # Unchanged

    async def test_update_hypothesis_with_string_uuid(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a hypothesis using string UUID."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Original Hypothesis",
            description="Original description",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        hypothesis_id_str = str(hypothesis.id)
        updated_hypothesis = await hypothesis_repository.update(
            hypothesis_id_str,
            title="Updated Hypothesis Title String",
            description="Updated description string",
        )

        assert updated_hypothesis.title == "Updated Hypothesis Title String"
        assert updated_hypothesis.description == "Updated description string"
        assert updated_hypothesis.id == hypothesis.id

    async def test_update_hypothesis_partial_fields(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating only some fields of a hypothesis."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Original Hypothesis",
            description="Original description",
            author="Original Author",
            status=HypothesisStatus.PROPOSED,
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Update only title
        updated_hypothesis = await hypothesis_repository.update(
            hypothesis.id, title="Updated Title Only"
        )

        assert updated_hypothesis.title == "Updated Title Only"
        assert updated_hypothesis.description == "Original description"  # Unchanged
        assert updated_hypothesis.status == HypothesisStatus.PROPOSED  # Unchanged
        assert updated_hypothesis.id == hypothesis.id

    async def test_update_hypothesis_target_metrics(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating a hypothesis's target metrics."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis with Metrics",
            author="Test Author",
            target_metrics=["accuracy"],
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Update target metrics
        updated_metrics = ["accuracy", "precision", "recall"]
        updated_hypothesis = await hypothesis_repository.update(
            hypothesis.id, target_metrics=updated_metrics
        )

        assert updated_hypothesis.target_metrics == updated_metrics
        assert updated_hypothesis.title == "Hypothesis with Metrics"  # Unchanged

    async def test_list_hypotheses(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing all hypotheses."""
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

        # Create multiple hypotheses
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 1",
            description="First hypothesis",
            author="Author 1",
        )
        hypothesis2 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 2",
            description="Second hypothesis",
            author="Author 2",
        )
        db_session.add_all([hypothesis1, hypothesis2])
        await db_session.flush()
        await db_session.refresh(hypothesis1)
        await db_session.refresh(hypothesis2)

        hypotheses = await hypothesis_repository.list()

        assert len(hypotheses) >= 2
        hypothesis_titles = [h.title for h in hypotheses]
        assert "Hypothesis 1" in hypothesis_titles
        assert "Hypothesis 2" in hypothesis_titles

    async def test_list_hypotheses_with_limit(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing hypotheses with a limit."""
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

        # Create multiple hypotheses
        for i in range(5):
            hypothesis = Hypothesis(
                id=None,
                project_id=project.id,
                title=f"Hypothesis {i}",
                description=f"Hypothesis {i} description",
                author=f"Author {i}",
            )
            db_session.add(hypothesis)
        await db_session.flush()

        # List with limit
        hypotheses = await hypothesis_repository.list(ListOptions(limit=3))

        assert len(hypotheses) <= 3

    async def test_list_hypotheses_with_offset(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test listing hypotheses with an offset."""
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

        # Create multiple hypotheses
        hypothesis_ids = []
        for i in range(5):
            hypothesis = Hypothesis(
                id=None,
                project_id=project.id,
                title=f"Hypothesis {i}",
                description=f"Hypothesis {i} description",
                author=f"Author {i}",
            )
            db_session.add(hypothesis)
            await db_session.flush()
            await db_session.refresh(hypothesis)
            hypothesis_ids.append(hypothesis.id)

        # List with offset
        hypotheses = await hypothesis_repository.list(ListOptions(limit=2, offset=2))

        assert len(hypotheses) <= 2

    async def test_delete_hypothesis(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting a hypothesis using string UUID."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis to Delete",
            description="This hypothesis will be deleted",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Verify hypothesis exists
        retrieved_hypothesis = await hypothesis_repository.get_by_id(hypothesis.id)
        assert retrieved_hypothesis is not None

        # Delete the hypothesis
        hypothesis_id_str = str(hypothesis.id)
        await hypothesis_repository.delete(hypothesis_id_str)

        # Verify hypothesis is deleted
        with pytest.raises(DBNotFoundError):
            await hypothesis_repository.get_by_id(hypothesis.id)

    async def test_delete_hypothesis_with_uuid_object(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting a hypothesis using UUID object."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis to Delete",
            description="This hypothesis will be deleted",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Verify hypothesis exists
        retrieved_hypothesis = await hypothesis_repository.get_by_id(hypothesis.id)
        assert retrieved_hypothesis is not None

        # Delete using UUID object
        await hypothesis_repository.delete(hypothesis.id)

        # Verify hypothesis is deleted
        with pytest.raises(DBNotFoundError):
            await hypothesis_repository.get_by_id(hypothesis.id)

    async def test_upsert_create_new(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test upsert creating a new hypothesis."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Upsert Hypothesis",
            description="Hypothesis created via upsert",
            author="Test Author",
        )

        # First create it normally to get an ID
        created_hypothesis = await hypothesis_repository.create(hypothesis)
        hypothesis_id = created_hypothesis.id

        # Now upsert with same ID should update
        updated_hypothesis = Hypothesis(
            id=hypothesis_id,
            project_id=project.id,
            title="Upserted Hypothesis",
            description="Updated via upsert",
            author="Test Author",
        )

        result = await hypothesis_repository.upsert(updated_hypothesis)

        assert result.id == hypothesis_id
        assert result.title == "Upserted Hypothesis"
        assert result.description == "Updated via upsert"

    async def test_upsert_update_existing(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test upsert updating an existing hypothesis."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Original Hypothesis",
            description="Original description",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Modify the hypothesis
        hypothesis.title = "Upserted Title"
        hypothesis.description = "Upserted Description"

        result = await hypothesis_repository.upsert(hypothesis)

        assert result.id == hypothesis.id
        assert result.title == "Upserted Title"
        assert result.description == "Upserted Description"

    async def test_get_single(
        self,
        hypothesis_repository: HypothesisRepository,
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Test Hypothesis",
            description="Test description",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        retrieved_hypothesis = await hypothesis_repository.get_single(hypothesis.id)

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id
        assert retrieved_hypothesis.title == hypothesis.title

    async def test_get_single_not_found(
        self, hypothesis_repository: HypothesisRepository
    ):
        """Test get_single raises DBNotFoundError for non-existent hypothesis."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await hypothesis_repository.get_single(non_existent_id)

    # Custom Methods Tests

    async def test_get_accessible_hypotheses_owned_by_user(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting hypotheses owned by the user."""
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

        # Create hypotheses in these projects
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project1.id,
            title="Hypothesis 1",
            description="First hypothesis",
            author="Author 1",
        )
        hypothesis2 = Hypothesis(
            id=None,
            project_id=project2.id,
            title="Hypothesis 2",
            description="Second hypothesis",
            author="Author 2",
        )
        db_session.add_all([hypothesis1, hypothesis2])
        await db_session.flush()
        await db_session.refresh(hypothesis1)
        await db_session.refresh(hypothesis2)

        # Get accessible hypotheses
        accessible_hypotheses = await hypothesis_repository.get_accessible_hypotheses(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_hypotheses) >= 2
        hypothesis_ids = [h.id for h in accessible_hypotheses]
        assert hypothesis1.id in hypothesis_ids
        assert hypothesis2.id in hypothesis_ids

    async def test_get_accessible_hypotheses_via_team(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting hypotheses accessible via team membership."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team with Hypotheses",
            description="Team with accessible hypotheses",
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

        # Create hypotheses in the project
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Team Hypothesis 1",
            description="First team hypothesis",
            author="Author 1",
        )
        hypothesis2 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Team Hypothesis 2",
            description="Second team hypothesis",
            author="Author 2",
        )
        db_session.add_all([hypothesis1, hypothesis2])
        await db_session.flush()
        await db_session.refresh(hypothesis1)
        await db_session.refresh(hypothesis2)

        # Get accessible hypotheses
        accessible_hypotheses = await hypothesis_repository.get_accessible_hypotheses(
            test_user  # type: ignore[arg-type]
        )

        assert len(accessible_hypotheses) >= 2
        hypothesis_ids = [h.id for h in accessible_hypotheses]
        assert hypothesis1.id in hypothesis_ids
        assert hypothesis2.id in hypothesis_ids

    async def test_get_accessible_hypotheses_ordered_by_created_at_desc(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that accessible hypotheses are ordered by created_at descending."""
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

        # Create hypotheses with slight time differences
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 1",
            description="First hypothesis",
            author="Author 1",
        )
        db_session.add(hypothesis1)
        await db_session.flush()
        await db_session.refresh(hypothesis1)

        # Small delay to ensure different timestamps
        import asyncio

        await asyncio.sleep(0.01)

        hypothesis2 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 2",
            description="Second hypothesis",
            author="Author 2",
        )
        db_session.add(hypothesis2)
        await db_session.flush()
        await db_session.refresh(hypothesis2)

        # Get accessible hypotheses
        accessible_hypotheses = await hypothesis_repository.get_accessible_hypotheses(
            test_user  # type: ignore[arg-type]
        )

        # Find our hypotheses in the list
        hypothesis1_idx = next(
            (i for i, h in enumerate(accessible_hypotheses) if h.id == hypothesis1.id),
            None,
        )
        hypothesis2_idx = next(
            (i for i, h in enumerate(accessible_hypotheses) if h.id == hypothesis2.id),
            None,
        )

        assert hypothesis1_idx is not None
        assert hypothesis2_idx is not None
        # Hypothesis 2 (created later) should come before Hypothesis 1
        assert hypothesis2_idx < hypothesis1_idx

    async def test_get_accessible_hypotheses_no_access(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that user cannot access hypotheses they don't own or belong to."""
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

        # Create hypothesis in inaccessible project
        inaccessible_hypothesis = Hypothesis(
            id=None,
            project_id=inaccessible_project.id,
            title="Inaccessible Hypothesis",
            description="Hypothesis user cannot access",
            author="Author",
        )
        db_session.add(inaccessible_hypothesis)
        await db_session.flush()
        await db_session.refresh(inaccessible_hypothesis)

        # Get accessible hypotheses
        accessible_hypotheses = await hypothesis_repository.get_accessible_hypotheses(
            test_user  # type: ignore[arg-type]
        )

        hypothesis_ids = [h.id for h in accessible_hypotheses]
        assert inaccessible_hypothesis.id not in hypothesis_ids

    async def test_get_hypotheses_by_project(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting hypotheses by project ID."""
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

        # Create hypotheses in the project
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 1",
            description="First hypothesis",
            author="Author 1",
        )
        hypothesis2 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 2",
            description="Second hypothesis",
            author="Author 2",
        )
        db_session.add_all([hypothesis1, hypothesis2])
        await db_session.flush()
        await db_session.refresh(hypothesis1)
        await db_session.refresh(hypothesis2)

        # Get hypotheses by project
        hypotheses = await hypothesis_repository.get_hypotheses_by_project(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert len(hypotheses) == 2
        hypothesis_ids = [h.id for h in hypotheses]
        assert hypothesis1.id in hypothesis_ids
        assert hypothesis2.id in hypothesis_ids

    async def test_get_hypotheses_by_project_ordered_by_created_at_desc(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that hypotheses are ordered by created_at descending."""
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

        # Create hypotheses with different timestamps
        hypothesis1 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 1",
            author="Author 1",
        )
        db_session.add(hypothesis1)
        await db_session.flush()
        await db_session.refresh(hypothesis1)

        import asyncio

        await asyncio.sleep(0.01)

        hypothesis2 = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis 2",
            author="Author 2",
        )
        db_session.add(hypothesis2)
        await db_session.flush()
        await db_session.refresh(hypothesis2)

        # Get hypotheses by project
        hypotheses = await hypothesis_repository.get_hypotheses_by_project(
            test_user, project.id  # type: ignore[arg-type]
        )

        assert len(hypotheses) == 2
        # Hypothesis 2 (created later) should come before Hypothesis 1
        assert hypotheses[0].id == hypothesis2.id
        assert hypotheses[1].id == hypothesis1.id

    async def test_get_hypotheses_by_project_inaccessible_project(
        self,
        hypothesis_repository: HypothesisRepository,
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

        # Create hypothesis in inaccessible project
        hypothesis = Hypothesis(
            id=None,
            project_id=inaccessible_project.id,
            title="Hypothesis",
            description="Hypothesis in inaccessible project",
            author="Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Get hypotheses by project (should return empty list)
        hypotheses = await hypothesis_repository.get_hypotheses_by_project(
            test_user, inaccessible_project.id  # type: ignore[arg-type]
        )

        assert len(hypotheses) == 0

    async def test_get_hypotheses_by_project_nonexistent_project(
        self,
        hypothesis_repository: HypothesisRepository,
        test_user: User,
    ):
        """Test getting hypotheses for non-existent project returns empty list."""
        nonexistent_id = uuid4()
        hypotheses = await hypothesis_repository.get_hypotheses_by_project(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert len(hypotheses) == 0

    async def test_get_hypothesis_if_accessible_owned_project(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a hypothesis that user owns."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Owned Hypothesis",
            description="Hypothesis owned by user",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Get hypothesis by ID
        retrieved_hypothesis = await hypothesis_repository.get_hypothesis_if_accessible(
            test_user, hypothesis.id  # type: ignore[arg-type]
        )

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id
        assert retrieved_hypothesis.title == hypothesis.title
        assert retrieved_hypothesis.project_id == project.id

    async def test_get_hypothesis_if_accessible_via_team(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a hypothesis accessible via team membership."""
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

        # Create hypothesis in project
        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Team Hypothesis",
            description="Hypothesis in team",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Get hypothesis by ID
        retrieved_hypothesis = await hypothesis_repository.get_hypothesis_if_accessible(
            test_user, hypothesis.id  # type: ignore[arg-type]
        )

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id
        assert retrieved_hypothesis.project_id == project.id

    async def test_get_hypothesis_if_accessible_not_accessible(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test that inaccessible hypothesis returns None."""
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

        # Create hypothesis in inaccessible project
        inaccessible_hypothesis = Hypothesis(
            id=None,
            project_id=inaccessible_project.id,
            title="Inaccessible Hypothesis",
            description="Hypothesis user cannot access",
            author="Test Author",
        )
        db_session.add(inaccessible_hypothesis)
        await db_session.flush()
        await db_session.refresh(inaccessible_hypothesis)

        # Try to get hypothesis by ID
        retrieved_hypothesis = await hypothesis_repository.get_hypothesis_if_accessible(
            test_user, inaccessible_hypothesis.id  # type: ignore[arg-type]
        )

        assert retrieved_hypothesis is None

    async def test_get_hypothesis_if_accessible_with_string_uuid(
        self,
        hypothesis_repository: HypothesisRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test getting a hypothesis using string UUID."""
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

        hypothesis = Hypothesis(
            id=None,
            project_id=project.id,
            title="Hypothesis with String UUID",
            description="Testing string UUID",
            author="Test Author",
        )
        db_session.add(hypothesis)
        await db_session.flush()
        await db_session.refresh(hypothesis)

        # Get hypothesis using string UUID
        hypothesis_id_str = str(hypothesis.id)
        retrieved_hypothesis = await hypothesis_repository.get_hypothesis_if_accessible(
            test_user, hypothesis_id_str  # type: ignore[arg-type]
        )

        assert retrieved_hypothesis is not None
        assert retrieved_hypothesis.id == hypothesis.id

    async def test_get_hypothesis_if_accessible_nonexistent_hypothesis(
        self,
        hypothesis_repository: HypothesisRepository,
        test_user: User,
    ):
        """Test getting a non-existent hypothesis returns None."""
        nonexistent_id = uuid4()
        retrieved_hypothesis = await hypothesis_repository.get_hypothesis_if_accessible(
            test_user, nonexistent_id  # type: ignore[arg-type]
        )

        assert retrieved_hypothesis is None

