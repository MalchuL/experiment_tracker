"""
Tests for TeamRepository.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from models import Team, TeamMember, User
from domain.team.teams.repository import TeamRepository
from lib.db.error import DBNotFoundError


class TestTeamRepository:
    """Test suite for TeamRepository."""

    async def test_create_team(self, team_repository: TeamRepository, test_user: User):
        """Test creating a new team."""
        team = Team(
            id=None,
            name="New Team",
            description="A new team",
            owner_id=test_user.id,
        )

        created_team = await team_repository.create(team)

        assert created_team.id is not None
        assert created_team.name == "New Team"
        assert created_team.description == "A new team"
        assert created_team.owner_id == test_user.id

    async def test_created_at_is_naive_utc(
        self, team_repository: TeamRepository, test_user: User
    ):
        """Test that created_at is a naive UTC datetime (no timezone info)."""
        team = Team(
            id=None,
            name="Team with Timestamp",
            description="Testing timestamp format",
            owner_id=test_user.id,
        )

        created_team = await team_repository.create(team)

        # Verify created_at exists and is a datetime
        assert created_team.created_at is not None
        assert isinstance(created_team.created_at, datetime)

        # Verify it's timezone-naive (no tzinfo)
        assert created_team.created_at.tzinfo is None, (
            f"created_at should be timezone-naive but has tzinfo: "
            f"{created_team.created_at.tzinfo}"
        )

        # Verify it's close to current UTC time (within 5 seconds)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = abs((created_team.created_at - now_utc).total_seconds())
        assert time_diff < 5, (
            f"created_at should be close to current UTC time. "
            f"Difference: {time_diff} seconds"
        )

    async def test_get_by_id(self, team_repository: TeamRepository, test_team: Team):
        """Test retrieving a team by ID using UUID object."""
        retrieved_team = await team_repository.get_by_id(test_team.id)

        assert retrieved_team is not None
        assert retrieved_team.id == test_team.id
        assert retrieved_team.name == test_team.name
        assert retrieved_team.owner_id == test_team.owner_id

    async def test_retrieved_team_has_naive_utc_timestamp(
        self, team_repository: TeamRepository, test_team: Team
    ):
        """Test that retrieved team's created_at is naive UTC datetime."""
        retrieved_team = await team_repository.get_by_id(test_team.id)

        assert retrieved_team is not None
        assert retrieved_team.created_at is not None
        assert isinstance(retrieved_team.created_at, datetime)

        # Verify it's timezone-naive
        assert retrieved_team.created_at.tzinfo is None, (
            f"Retrieved created_at should be timezone-naive but has tzinfo: "
            f"{retrieved_team.created_at.tzinfo}"
        )

    async def test_get_by_id_with_string_uuid(
        self, team_repository: TeamRepository, test_team: Team
    ):
        """Test retrieving a team by ID using string UUID."""
        team_id_str = str(test_team.id)
        retrieved_team = await team_repository.get_by_id(team_id_str)

        assert retrieved_team is not None
        assert retrieved_team.id == test_team.id
        assert retrieved_team.name == test_team.name
        assert retrieved_team.owner_id == test_team.owner_id

    async def test_get_by_id_not_found(self, team_repository: TeamRepository):
        """Test retrieving a non-existent team raises DBNotFoundError."""
        non_existent_id = uuid4()
        with pytest.raises(DBNotFoundError):
            await team_repository.get_by_id(non_existent_id)

    async def test_get_by_id_not_found_with_string_uuid(
        self, team_repository: TeamRepository
    ):
        """Test retrieving a non-existent team raises DBNotFoundError when using string UUID."""
        non_existent_id_str = str(uuid4())
        with pytest.raises(DBNotFoundError):
            await team_repository.get_by_id(non_existent_id_str)

    async def test_update_team(self, team_repository: TeamRepository, test_team: Team):
        """Test updating a team using UUID object."""
        # Use the UUID object directly for the update
        updated_team = await team_repository.update(
            test_team.id,  # Pass UUID object directly
            name="Updated Team Name",
            description="Updated description",
        )

        assert updated_team.name == "Updated Team Name"
        assert updated_team.description == "Updated description"
        assert updated_team.id == test_team.id

    async def test_update_team_with_string_uuid(
        self, team_repository: TeamRepository, db_session, test_user: User
    ):
        """Test updating a team using string UUID."""
        # Create a fresh team for this test to avoid conflicts
        team = Team(
            id=None,
            name="Original Team Name",
            description="Original description",
            owner_id=test_user.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Verify the team exists first
        retrieved_before = await team_repository.get_by_id(str(team.id))
        assert retrieved_before is not None
        assert retrieved_before.name == "Original Team Name"

        # Update using string UUID
        team_id_str = str(team.id)
        updated_team = await team_repository.update(
            team_id_str,
            name="Updated Team Name String",
            description="Updated description string",
        )

        # Verify the update worked
        assert updated_team.name == "Updated Team Name String"
        assert updated_team.description == "Updated description string"
        assert updated_team.id == team.id

        # Verify by retrieving again
        retrieved_after = await team_repository.get_by_id(team.id)
        assert retrieved_after is not None
        assert retrieved_after.name == "Updated Team Name String"

    async def test_list_teams(
        self, team_repository: TeamRepository, db_session, test_user: User
    ):
        """Test listing all teams."""
        # Create multiple teams
        team1 = Team(
            id=None,
            name="Team 1",
            description="First team",
            owner_id=test_user.id,
        )
        team2 = Team(
            id=None,
            name="Team 2",
            description="Second team",
            owner_id=test_user.id,
        )

        await team_repository.create(team1)
        await team_repository.create(team2)

        teams = await team_repository.list()

        assert len(teams) >= 2
        team_names = [team.name for team in teams]
        assert "Team 1" in team_names
        assert "Team 2" in team_names

        # Verify all listed teams have naive UTC timestamps
        for team in teams:
            assert team.created_at.tzinfo is None, (
                f"Team {team.id} created_at should be timezone-naive but has tzinfo: "
                f"{team.created_at.tzinfo}"
            )

    async def test_delete_team(self, team_repository: TeamRepository, test_team: Team):
        """Test deleting a team using string UUID."""
        team_id = str(test_team.id)

        # Verify team exists
        team = await team_repository.get_by_id(test_team.id)
        assert team is not None

        # Delete the team - use the team_id from the retrieved team to ensure compatibility
        delete_id = str(team.id) if team else team_id
        await team_repository.delete(delete_id)

        # Verify team is deleted
        with pytest.raises(DBNotFoundError):
            await team_repository.get_by_id(test_team.id)

    async def test_delete_team_with_uuid_object(
        self, team_repository: TeamRepository, db_session, test_user: User
    ):
        """Test deleting a team using UUID object."""
        # Create a new team for this test
        team = Team(
            id=None,
            name="Team to Delete",
            description="This team will be deleted",
            owner_id=test_user.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Verify team exists
        retrieved_team = await team_repository.get_by_id(team.id)
        assert retrieved_team is not None

        # Delete using UUID object
        await team_repository.delete(team.id)

        # Verify team is deleted
        with pytest.raises(DBNotFoundError):
            await team_repository.get_by_id(team.id)

    async def test_get_accessible_teams_single_member(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting teams accessible to a user who is a member."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team with Member",
            description="Team that test_user is a member of",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Verify team's created_at is naive UTC
        assert team.created_at.tzinfo is None, (
            f"Team created_at should be timezone-naive but has tzinfo: "
            f"{team.created_at.tzinfo}"
        )

        # Add test_user as a member
        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.flush()

        # Verify team_member's joined_at is naive UTC
        assert team_member.joined_at.tzinfo is None, (
            f"TeamMember joined_at should be timezone-naive but has tzinfo: "
            f"{team_member.joined_at.tzinfo}"
        )

        # Get accessible teams for test_user
        accessible_teams = await team_repository.get_accessible_teams(test_user)

        assert len(accessible_teams) >= 1
        team_ids = [t.id for t in accessible_teams]
        assert team.id in team_ids

        # Verify all accessible teams have naive UTC timestamps
        for accessible_team in accessible_teams:
            assert accessible_team.created_at.tzinfo is None, (
                f"Accessible team {accessible_team.id} created_at should be "
                f"timezone-naive but has tzinfo: {accessible_team.created_at.tzinfo}"
            )

    async def test_get_accessible_teams_multiple_teams(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting multiple teams accessible to a user."""
        # Create multiple teams
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
        team3 = Team(
            id=None,
            name="Team 3",
            description="Third team (not accessible)",
            owner_id=test_user_2.id,
        )

        db_session.add_all([team1, team2, team3])
        await db_session.flush()
        await db_session.refresh(team1)
        await db_session.refresh(team2)
        await db_session.refresh(team3)

        # Add test_user as member of team1 and team2, but not team3
        member1 = TeamMember(
            id=None,
            team_id=team1.id,
            user_id=test_user.id,
        )
        member2 = TeamMember(
            id=None,
            team_id=team2.id,
            user_id=test_user.id,
        )
        db_session.add_all([member1, member2])
        await db_session.flush()

        # Get accessible teams
        accessible_teams = await team_repository.get_accessible_teams(test_user)

        assert len(accessible_teams) >= 2
        accessible_team_ids = [t.id for t in accessible_teams]
        assert team1.id in accessible_team_ids
        assert team2.id in accessible_team_ids
        assert team3.id not in accessible_team_ids

    async def test_get_accessible_teams_no_teams(
        self,
        team_repository: TeamRepository,
        test_user: User,
    ):
        """Test getting accessible teams for a user with no team memberships."""
        accessible_teams = await team_repository.get_accessible_teams(test_user)

        assert isinstance(accessible_teams, list)
        assert len(accessible_teams) == 0

    async def test_user_created_at_is_naive_utc(self, test_user: User):
        """Test that user's created_at is naive UTC datetime."""
        # Verify created_at exists and is a datetime
        assert test_user.created_at is not None
        assert isinstance(test_user.created_at, datetime)

        # Verify it's timezone-naive (no tzinfo)
        assert test_user.created_at.tzinfo is None, (
            f"User created_at should be timezone-naive but has tzinfo: "
            f"{test_user.created_at.tzinfo}"
        )

        # Verify it's close to current UTC time (within 5 seconds)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = abs((test_user.created_at - now_utc).total_seconds())
        assert time_diff < 5, (
            f"User created_at should be close to current UTC time. "
            f"Difference: {time_diff} seconds"
        )

    async def test_get_accessible_teams_owner_not_automatically_member(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that team owner is not automatically included in accessible teams."""
        # Create a team owned by test_user
        team = Team(
            id=None,
            name="Owned Team",
            description="Team owned by test_user",
            owner_id=test_user.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Note: Owner is not automatically a member unless explicitly added
        accessible_teams = await team_repository.get_accessible_teams(test_user)

        # Owner should not be in accessible teams unless explicitly added as member
        accessible_team_ids = [t.id for t in accessible_teams]
        assert team.id not in accessible_team_ids

    async def test_upsert_create_new(
        self, team_repository: TeamRepository, test_user: User
    ):
        """Test upsert creating a new team."""
        team = Team(
            id=None,
            name="Upsert Team",
            description="Team created via upsert",
            owner_id=test_user.id,
        )

        # First create it normally to get an ID
        created_team = await team_repository.create(team)
        team_id = created_team.id

        # Now upsert with same ID should update
        updated_team = Team(
            id=team_id,
            name="Upserted Team",
            description="Updated via upsert",
            owner_id=test_user.id,
        )

        result = await team_repository.upsert(updated_team)

        assert result.id == team_id
        assert result.name == "Upserted Team"
        assert result.description == "Updated via upsert"

    async def test_upsert_update_existing(
        self, team_repository: TeamRepository, test_team: Team
    ):
        """Test upsert updating an existing team."""
        # Modify the team
        test_team.name = "Upserted Name"
        test_team.description = "Upserted Description"

        result = await team_repository.upsert(test_team)

        assert result.id == test_team.id
        assert result.name == "Upserted Name"
        assert result.description == "Upserted Description"

    async def test_get_team_member_if_accessible_exists_with_uuid(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member when it exists using UUID objects."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team for Member Test",
            description="Team for testing member access",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add test_user as a member
        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)

        # Get the team member using UUID objects
        result = await team_repository.get_team_member_if_accessible(
            test_user.id, team.id
        )

        assert result is not None
        assert result.id == team_member.id
        assert result.user_id == test_user.id
        assert result.team_id == team.id

    async def test_get_team_member_if_accessible_exists_with_string_uuid(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member when it exists using string UUIDs."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team for Member Test String",
            description="Team for testing member access with strings",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add test_user as a member
        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)

        # Get the team member using string UUIDs
        result = await team_repository.get_team_member_if_accessible(
            str(test_user.id), str(team.id)
        )

        assert result is not None
        assert result.id == team_member.id
        assert result.user_id == test_user.id
        assert result.team_id == team.id

    async def test_get_team_member_if_accessible_exists_with_mixed_uuid_types(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member when it exists using mixed UUID and string."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team for Member Test Mixed",
            description="Team for testing member access with mixed types",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add test_user as a member
        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)

        # Get the team member using mixed types (UUID for user_id, string for team_id)
        result = await team_repository.get_team_member_if_accessible(
            test_user.id, str(team.id)
        )

        assert result is not None
        assert result.id == team_member.id
        assert result.user_id == test_user.id
        assert result.team_id == team.id

        # Also test the reverse (string for user_id, UUID for team_id)
        result2 = await team_repository.get_team_member_if_accessible(
            str(test_user.id), team.id
        )

        assert result2 is not None
        assert result2.id == team_member.id
        assert result2.user_id == test_user.id
        assert result2.team_id == team.id

    async def test_get_team_member_if_accessible_not_found_with_uuid(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member when it doesn't exist using UUID objects."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team Without Member",
            description="Team that test_user is not a member of",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Try to get a team member that doesn't exist
        result = await team_repository.get_team_member_if_accessible(
            test_user.id, team.id
        )

        assert result is None

    async def test_get_team_member_if_accessible_not_found_with_string_uuid(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member when it doesn't exist using string UUIDs."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team Without Member String",
            description="Team that test_user is not a member of (string test)",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Try to get a team member that doesn't exist using string UUIDs
        result = await team_repository.get_team_member_if_accessible(
            str(test_user.id), str(team.id)
        )

        assert result is None

    async def test_get_team_member_if_accessible_not_found_nonexistent_ids(
        self, team_repository: TeamRepository
    ):
        """Test getting a team member with non-existent user and team IDs."""
        non_existent_user_id = uuid4()
        non_existent_team_id = uuid4()

        # Try to get a team member with non-existent IDs
        result = await team_repository.get_team_member_if_accessible(
            non_existent_user_id, non_existent_team_id
        )

        assert result is None

        # Also test with string UUIDs
        result2 = await team_repository.get_team_member_if_accessible(
            str(non_existent_user_id), str(non_existent_team_id)
        )

        assert result2 is None

    async def test_get_team_member_if_accessible_wrong_user(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member with wrong user ID."""
        # Create a team owned by test_user_2
        team = Team(
            id=None,
            name="Team for Wrong User Test",
            description="Team for testing wrong user access",
            owner_id=test_user_2.id,
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add test_user_2 as a member (not test_user)
        team_member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user_2.id,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)

        # Try to get team member with test_user (who is not a member)
        result = await team_repository.get_team_member_if_accessible(
            test_user.id, team.id
        )

        assert result is None

    async def test_get_team_member_if_accessible_wrong_team(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test getting a team member with wrong team ID."""
        # Create two teams
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

        # Add test_user as a member of team1 only
        team_member = TeamMember(
            id=None,
            team_id=team1.id,
            user_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.flush()
        await db_session.refresh(team_member)

        # Try to get team member with team2 (where test_user is not a member)
        result = await team_repository.get_team_member_if_accessible(
            test_user.id, team2.id
        )

        assert result is None
