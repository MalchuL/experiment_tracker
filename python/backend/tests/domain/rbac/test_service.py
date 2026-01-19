import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.error import InvalidScopeError
from domain.rbac.permissions.project import role_to_project_permissions
from domain.rbac.permissions.team import TeamActions, role_to_team_permissions
from domain.rbac.service import PermissionService
from models import Project, Team, Role, User


async def _create_team(db_session: AsyncSession, owner: User) -> Team:
    team = Team(
        id=None,
        name="Service Team",
        description="RBAC service team",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


async def _create_project(
    db_session: AsyncSession, owner: User, team: Team, name: str
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Service project",
        owner_id=owner.id,
        team_id=team.id,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestPermissionService:
    @pytest.fixture
    def permission_service(self, db_session: AsyncSession) -> PermissionService:
        return PermissionService(db_session, auto_commit=True)

    async def test_add_get_and_has_permission(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.DELETE_TEAM,
            allowed=False,
            team_id=team.id,
        )

        dto = await permission_service.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        permissions_by_action = {item.action: item.allowed for item in dto.data}
        assert permissions_by_action[TeamActions.VIEW_TEAM] is True
        assert permissions_by_action[TeamActions.DELETE_TEAM] is False

        assert (
            await permission_service.has_permission(
                test_user.id, TeamActions.VIEW_TEAM, team_id=team.id
            )
            is True
        )
        assert (
            await permission_service.has_permission(
                test_user.id, TeamActions.DELETE_TEAM, team_id=team.id
            )
            is False
        )

    async def test_manage_team_permissions_for_member(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project1 = await _create_project(db_session, test_user, team, "Project A")
        project2 = await _create_project(db_session, test_user, team, "Project B")

        await permission_service.add_user_to_team_permissions(
            user_id=test_user.id, team_id=team.id, role=Role.MEMBER
        )

        team_permissions = await permission_service.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        assert len(team_permissions.data) == len(role_to_team_permissions(Role.MEMBER))

        project_permissions_1 = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project1.id
        )
        project_permissions_2 = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project2.id
        )
        assert len(project_permissions_1.data) == len(
            role_to_project_permissions(Role.MEMBER)
        )
        assert len(project_permissions_2.data) == len(
            role_to_project_permissions(Role.MEMBER)
        )

        await permission_service.update_user_team_role_permissions(
            user_id=test_user.id, team_id=team.id, role=Role.ADMIN
        )
        updated_team_permissions = await permission_service.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        updated_map = {
            item.action: item.allowed for item in updated_team_permissions.data
        }
        assert updated_map == role_to_team_permissions(Role.ADMIN)

        await permission_service.remove_user_from_team_permissions(
            user_id=test_user.id, team_id=team.id
        )
        assert (
            await permission_service.get_permissions(
                user_id=test_user.id, team_id=team.id
            )
        ).data == []
        assert (
            await permission_service.get_permissions(
                user_id=test_user.id, project_id=project1.id
            )
        ).data == []

    async def test_get_permissions_requires_scope(
        self, permission_service: PermissionService
    ) -> None:
        with pytest.raises(
            InvalidScopeError,
            match="At least one of user_id, team_id, project_id must be provided.",
        ):
            await permission_service.get_permissions()
