import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.error import InvalidScopeError
from domain.rbac.permissions.project import ProjectActions, role_to_project_permissions
from domain.rbac.permissions.team import TeamActions, role_to_team_permissions
from domain.rbac.repository import PermissionRepository
from models import Permission, Project, Team, Role, User


async def _create_team(db_session: AsyncSession, owner: User) -> Team:
    team = Team(
        id=None,
        name="Test Team",
        description="RBAC test team",
        owner_id=owner.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


async def _create_project(
    db_session: AsyncSession, owner: User, team: Team | None = None
) -> Project:
    project = Project(
        id=None,
        name="Test Project",
        description="RBAC test project",
        owner_id=owner.id,
        team_id=team.id if team else None,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestPermissionRepository:
    @pytest.fixture
    def permission_repository(self, db_session: AsyncSession) -> PermissionRepository:
        return PermissionRepository(db_session)

    async def test_scope_required(self, permission_repository: PermissionRepository):
        with pytest.raises(
            InvalidScopeError,
            match="At least one of user_id, team_id, project_id must be provided.",
        ):
            await permission_repository.get_permissions()

    async def test_create_get_delete_permissions_by_team_scope(
        self,
        permission_repository: PermissionRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)

        permission = Permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )

        await permission_repository.create_permission(permission)

        permissions = await permission_repository.get_permissions(
            user_id=test_user.id,
            team_id=team.id,
            actions=TeamActions.VIEW_TEAM,
        )
        assert len(permissions) == 1
        assert permissions[0].action == TeamActions.VIEW_TEAM

        await permission_repository.delete_permission(permissions)
        deleted = await permission_repository.get_permissions(
            user_id=test_user.id,
            team_id=team.id,
            actions=TeamActions.VIEW_TEAM,
        )
        assert deleted == []

    async def test_project_scope_filters(
        self,
        permission_repository: PermissionRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        permission = Permission(
            user_id=test_user.id,
            action="project.view",
            allowed=True,
            project_id=project.id,
        )

        await permission_repository.create_permission(permission)
        permissions = await permission_repository.get_permissions(
            user_id=test_user.id, project_id=project.id
        )

        assert len(permissions) == 1
        assert permissions[0].project_id == project.id

    async def test_team_member_permissions_proxy_affects_team_projects_only(
        self,
        permission_repository: PermissionRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user_2)
        project_1 = await _create_project(db_session, test_user_2, team=team)
        project_2 = await _create_project(db_session, test_user_2, team=team)
        standalone = await _create_project(db_session, test_user_2)

        await permission_repository.add_team_member_permissions(
            team.id, test_user.id, Role.MEMBER
        )
        await permission_repository.add_team_member_permissions(
            team.id, test_user.id, Role.MEMBER
        )

        team_permissions = await permission_repository.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        assert len(team_permissions) == len(role_to_team_permissions(Role.MEMBER))

        project_permissions = await permission_repository.get_permissions(
            user_id=test_user.id, project_id=project_1.id
        )
        assert len(project_permissions) == len(role_to_project_permissions(Role.MEMBER))
        assert await permission_repository.get_permissions(
            user_id=test_user.id, project_id=project_2.id
        )
        assert (
            await permission_repository.get_permissions(
                user_id=test_user.id, project_id=standalone.id
            )
            == []
        )

        await permission_repository.update_team_member_role_permissions(
            team.id, test_user.id, Role.ADMIN
        )
        updated_team_permissions = await permission_repository.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        updated_map = {
            permission.action: permission.allowed
            for permission in updated_team_permissions
        }
        assert updated_map == role_to_team_permissions(Role.ADMIN)

        await permission_repository.remove_team_member_permissions(
            team.id, test_user.id
        )
        assert (
            await permission_repository.get_permissions(
                user_id=test_user.id, team_id=team.id
            )
            == []
        )
        assert (
            await permission_repository.get_permissions(
                user_id=test_user.id, project_id=project_1.id
            )
            == []
        )
        assert (
            await permission_repository.get_permissions(
                user_id=test_user.id, project_id=standalone.id
            )
            == []
        )

    async def test_get_user_accessible_projects_proxy_filters_actions(
        self,
        permission_repository: PermissionRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project_view = await _create_project(db_session, test_user)
        project_edit = await _create_project(db_session, test_user)

        await permission_repository.create_permission(
            Permission(
                user_id=test_user.id,
                action=ProjectActions.VIEW_PROJECT,
                allowed=True,
                project_id=project_view.id,
            )
        )
        await permission_repository.create_permission(
            Permission(
                user_id=test_user.id,
                action=ProjectActions.EDIT_PROJECT,
                allowed=True,
                project_id=project_edit.id,
            )
        )

        results = await permission_repository.get_user_accessible_projects(
            test_user.id, actions=ProjectActions.VIEW_PROJECT
        )
        assert {project.id for project in results} == {project_view.id}

    async def test_get_user_accessible_teams_proxy_excludes_unrelated(
        self,
        permission_repository: PermissionRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        accessible_team = await _create_team(db_session, test_user_2)
        hidden_team = await _create_team(db_session, test_user_2)

        await permission_repository.create_permission(
            Permission(
                user_id=test_user.id,
                action=TeamActions.VIEW_TEAM,
                allowed=True,
                team_id=accessible_team.id,
            )
        )
        await permission_repository.create_permission(
            Permission(
                user_id=test_user.id,
                action=TeamActions.MANAGE_TEAM,
                allowed=True,
                team_id=hidden_team.id,
            )
        )

        results = await permission_repository.get_user_accessible_teams(
            test_user.id, actions=TeamActions.VIEW_TEAM
        )
        assert {team.id for team in results} == {accessible_team.id}
