import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.permissions.team import TeamActions, role_to_team_permissions
from domain.rbac.repository import PermissionRepository
from domain.rbac.service import PermissionService
from domain.team.teams.dto import (
    TeamCreateDTO,
    TeamMemberCreateDTO,
    TeamMemberDeleteDTO,
    TeamMemberUpdateDTO,
    TeamUpdateDTO,
)
from domain.team.teams.errors import (
    TeamAccessDeniedError,
    TeamMemberAlreadyExistsError,
    TeamMemberNotFoundError,
)
from domain.team.teams.service import TeamService
from domain.team.teams.repository import TeamRepository
from models import Team, TeamMember, Role, User


async def _create_team(
    db_session: AsyncSession, owner: User, name: str = "Service Team"
) -> Team:
    team = Team(
        id=None,
        name=name,
        description="Team service test",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


async def _grant_manage_permission(db_session: AsyncSession, user_id, team_id) -> None:
    permission_service = PermissionService(db_session, auto_commit=True)
    await permission_service.add_permission(
        user_id=user_id,
        action=TeamActions.MANAGE_TEAM,
        allowed=True,
        team_id=team_id,
    )


class TestTeamService:
    @pytest.fixture
    def team_service(self, db_session: AsyncSession) -> TeamService:
        return TeamService(db_session)

    async def test_create_team_creates_owner_permissions(
        self, team_service: TeamService, db_session: AsyncSession, test_user: User
    ) -> None:
        dto = TeamCreateDTO(name="New Team", description="Created by service")

        created = await team_service.create_team(test_user.id, dto)

        assert created.id is not None
        assert created.name == "New Team"
        assert created.owner_id == test_user.id

        permission_repo = PermissionRepository(db_session)
        permissions = await permission_repo.get_permissions(
            user_id=test_user.id, team_id=created.id
        )
        permissions_map = {item.action: item.allowed for item in permissions}
        assert permissions_map == role_to_team_permissions(Role.OWNER)

    async def test_update_team_access_denied(
        self, team_service: TeamService, db_session: AsyncSession, test_user: User
    ) -> None:
        team = await _create_team(db_session, test_user)

        dto = TeamUpdateDTO(id=team.id, name="Updated", description="Updated")

        with pytest.raises(TeamAccessDeniedError):
            await team_service.update_team(test_user.id, dto)

    async def test_update_team_updates_fields(
        self, team_service: TeamService, db_session: AsyncSession, test_user: User
    ) -> None:
        team = await _create_team(db_session, test_user, name="Original")
        await _grant_manage_permission(db_session, test_user.id, team.id)

        dto = TeamUpdateDTO(id=team.id, name="Updated", description="New description")
        updated = await team_service.update_team(test_user.id, dto)

        assert updated.id == team.id
        assert updated.name == "Updated"
        assert updated.description == "New description"

    async def test_delete_team_access_denied(
        self, team_service: TeamService, db_session: AsyncSession, test_user: User
    ) -> None:
        team = await _create_team(db_session, test_user)

        with pytest.raises(TeamAccessDeniedError):
            await team_service.delete_team(test_user.id, team.id)

    async def test_delete_team_removes_team(
        self, team_service: TeamService, db_session: AsyncSession, test_user: User
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        await team_service.delete_team(test_user.id, team.id)

        remaining = await db_session.get(Team, team.id)
        assert remaining is None

    async def test_add_team_member_creates_permissions(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        dto = TeamMemberCreateDTO(
            user_id=test_user_2.id, team_id=team.id, role=Role.MEMBER
        )
        created = await team_service.add_team_member(test_user.id, dto)

        assert created.user_id == test_user_2.id
        assert created.team_id == team.id
        assert created.role == Role.MEMBER

        permission_repo = PermissionRepository(db_session)
        permissions = await permission_repo.get_permissions(
            user_id=test_user_2.id, team_id=team.id
        )
        permissions_map = {item.action: item.allowed for item in permissions}
        assert permissions_map == role_to_team_permissions(Role.MEMBER)

    async def test_add_team_member_existing_raises(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        db_session.add(
            TeamMember(
                id=None,
                team_id=team.id,
                user_id=test_user_2.id,
                role=Role.MEMBER,
            )
        )
        await db_session.flush()

        dto = TeamMemberCreateDTO(
            user_id=test_user_2.id, team_id=team.id, role=Role.MEMBER
        )
        with pytest.raises(TeamMemberAlreadyExistsError):
            await team_service.add_team_member(test_user.id, dto)

    async def test_update_team_member_updates_permissions(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        await team_service.add_team_member(
            test_user.id,
            TeamMemberCreateDTO(
                user_id=test_user_2.id, team_id=team.id, role=Role.MEMBER
            ),
        )

        await team_service.update_team_member(
            test_user.id,
            TeamMemberUpdateDTO(
                user_id=test_user_2.id, team_id=team.id, role=Role.ADMIN
            ),
        )

        permission_repo = PermissionRepository(db_session)
        permissions = await permission_repo.get_permissions(
            user_id=test_user_2.id, team_id=team.id
        )
        permissions_map = {item.action: item.allowed for item in permissions}
        assert permissions_map == role_to_team_permissions(Role.ADMIN)

    async def test_update_team_member_missing_raises(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        with pytest.raises(TeamMemberNotFoundError):
            await team_service.update_team_member(
                test_user.id,
                TeamMemberUpdateDTO(
                    user_id=test_user_2.id, team_id=team.id, role=Role.ADMIN
                ),
            )

    async def test_remove_team_member_self_does_not_require_permission(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        await _grant_manage_permission(db_session, test_user.id, team.id)

        await team_service.add_team_member(
            test_user.id,
            TeamMemberCreateDTO(
                user_id=test_user_2.id, team_id=team.id, role=Role.MEMBER
            ),
        )

        await team_service.remove_team_member(
            test_user_2.id,
            TeamMemberDeleteDTO(user_id=test_user_2.id, team_member_id=team.id),
        )

        team_repository = TeamRepository(db_session)
        remaining = await team_repository.get_team_member_if_accessible(
            test_user_2.id, team.id
        )
        assert remaining is None

    async def test_remove_team_member_requires_manage_permission(
        self,
        team_service: TeamService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user)

        db_session.add(
            TeamMember(
                id=None,
                team_id=team.id,
                user_id=test_user_2.id,
                role=Role.MEMBER,
            )
        )
        await db_session.flush()

        with pytest.raises(TeamAccessDeniedError):
            await team_service.remove_team_member(
                test_user.id,
                TeamMemberDeleteDTO(user_id=test_user_2.id, team_member_id=team.id),
            )
