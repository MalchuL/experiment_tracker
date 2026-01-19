import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.team.teams.errors import TeamMemberNotFoundError
from domain.team.teams.repository import TeamRepository
from models import Team, TeamMember, Role, User


async def _create_team(
    db_session: AsyncSession, owner: User, name: str = "Team Repo"
) -> Team:
    team = Team(
        id=None,
        name=name,
        description="Team repository test",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


class TestTeamRepository:
    @pytest.fixture
    def team_repository(self, db_session: AsyncSession) -> TeamRepository:
        return TeamRepository(db_session)

    async def test_add_update_delete_team_member(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)

        member = TeamMember(
            id=None,
            team_id=team.id,
            user_id=test_user_2.id,
            role=Role.MEMBER,
        )
        created = await team_repository.add_team_member(member)
        assert created.id is not None

        fetched = await team_repository.get_team_member_if_accessible(
            test_user_2.id, team.id
        )
        assert fetched is not None
        assert fetched.role == Role.MEMBER

        created.role = Role.ADMIN
        await team_repository.update_team_member(created)
        updated = await team_repository.get_team_member_if_accessible(
            test_user_2.id, team.id
        )
        assert updated is not None
        assert updated.role == Role.ADMIN

        await team_repository.delete_team_member(test_user_2.id, team.id)
        assert (
            await team_repository.get_team_member_if_accessible(test_user_2.id, team.id)
            is None
        )

        with pytest.raises(TeamMemberNotFoundError):
            await team_repository.delete_team_member(test_user_2.id, team.id)

    async def test_get_accessible_teams_filters_by_membership(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        accessible_team = await _create_team(db_session, test_user_2, name="Allowed")
        hidden_team = await _create_team(db_session, test_user_2, name="Hidden")

        db_session.add(
            TeamMember(
                id=None,
                team_id=accessible_team.id,
                user_id=test_user.id,
                role=Role.MEMBER,
            )
        )
        await db_session.flush()

        teams = await team_repository.get_accessible_teams(test_user)
        team_ids = {team.id for team in teams}
        assert accessible_team.id in team_ids
        assert hidden_team.id not in team_ids

    async def test_get_teams_by_ids_returns_empty_for_empty_list(
        self, team_repository: TeamRepository
    ) -> None:
        assert await team_repository.get_teams_by_ids([]) == []

    async def test_get_teams_by_ids_returns_requested_teams(
        self,
        team_repository: TeamRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team_1 = await _create_team(db_session, test_user, name="Team One")
        team_2 = await _create_team(db_session, test_user, name="Team Two")

        teams = await team_repository.get_teams_by_ids([team_1.id, team_2.id])
        team_ids = {team.id for team in teams}
        assert team_ids == {team_1.id, team_2.id}

    async def test_get_team_member_if_accessible_requires_team_id(
        self, team_repository: TeamRepository, test_user: User
    ) -> None:
        with pytest.raises(ValueError, match="Team ID is required"):
            await team_repository.get_team_member_if_accessible(test_user.id, None)
