from uuid import uuid4

from lib.db.error import DBNotFoundError
import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.error import InvalidScopeError
from domain.rbac.permissions.project import (
    ProjectActions,
    role_to_project_permissions,
)
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
    db_session: AsyncSession, owner: User, team: Team | None, name: str
) -> Project:
    project = Project(
        id=None,
        name=name,
        description="Service project",
        owner_id=owner.id,
        team_id=team.id if team else None,
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
        expected_team_actions = role_to_team_permissions(
            Role.MEMBER
        ) | role_to_project_permissions(Role.MEMBER)
        assert len(team_permissions.data) == len(expected_team_actions)

        project_permissions_1 = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project1.id
        )
        project_permissions_2 = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project2.id
        )
        assert project_permissions_1.data == []
        assert project_permissions_2.data == []

        await permission_service.update_user_team_role_permissions(
            user_id=test_user.id, team_id=team.id, role=Role.ADMIN
        )
        updated_team_permissions = await permission_service.get_permissions(
            user_id=test_user.id, team_id=team.id
        )
        updated_map = {
            item.action: item.allowed for item in updated_team_permissions.data
        }
        expected_updated_actions = role_to_team_permissions(
            Role.ADMIN
        ) | role_to_project_permissions(Role.ADMIN)
        assert updated_map == expected_updated_actions

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

    async def test_manage_project_permissions_for_member(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user, None, "Project A")

        await permission_service.add_user_to_project_permissions(
            user_id=test_user.id, project_id=project.id, role=Role.MEMBER
        )
        await permission_service.add_user_to_project_permissions(
            user_id=test_user.id, project_id=project.id, role=Role.MEMBER
        )

        project_permissions = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        assert len(project_permissions.data) == len(
            role_to_project_permissions(Role.MEMBER)
        )

        await permission_service.update_user_project_role_permissions(
            user_id=test_user.id, project_id=project.id, role=Role.VIEWER
        )
        updated_permissions = await permission_service.get_permissions(
            user_id=test_user.id, project_id=project.id
        )
        updated_map = {item.action: item.allowed for item in updated_permissions.data}
        assert updated_map == role_to_project_permissions(Role.VIEWER)

        await permission_service.remove_user_from_project_permissions(
            user_id=test_user.id, project_id=project.id
        )
        assert (
            await permission_service.get_permissions(
                user_id=test_user.id, project_id=project.id
            )
        ).data == []

    async def test_project_permission_with_team_falls_back_to_team_when_missing(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project = await _create_project(db_session, test_user, team, "Team Project")

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )

        assert (
            await permission_service.has_permission(
                test_user.id, TeamActions.VIEW_TEAM, project_id=project.id
            )
            is True
        )

    async def test_project_permission_denies_even_if_team_allows(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project = await _create_project(
            db_session, test_user, team, "Restricted Project"
        )

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=False,
            project_id=project.id,
        )

        assert (
            await permission_service.has_permission(
                test_user.id, TeamActions.VIEW_TEAM, project_id=project.id
            )
            is False
        )

    async def test_project_without_team_only_checks_project_permissions(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        project = await _create_project(
            db_session, test_user, None, "Standalone Project"
        )

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )

        assert (
            await permission_service.has_permission(
                test_user.id, TeamActions.VIEW_TEAM, project_id=project.id
            )
            is False
        )

    async def test_get_user_accessible_project_ids_merges_team_and_project_permissions(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team = await _create_team(db_session, test_user_2)
        team_project = await _create_project(
            db_session, test_user_2, team, "Team Project"
        )
        standalone_project = await _create_project(
            db_session, test_user_2, None, "Standalone Project"
        )
        other_team = await _create_team(db_session, test_user_2)
        other_team_project = await _create_project(
            db_session, test_user_2, other_team, "Other Team Project"
        )

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=True,
            project_id=standalone_project.id,
        )

        project_ids = await permission_service.get_user_accessible_project_ids(
            test_user.id
        )
        assert set(project_ids) == {team_project.id, standalone_project.id}
        assert other_team_project.id not in project_ids

    async def test_get_user_accessible_project_ids_excludes_denied_permissions(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _create_project(db_session, test_user_2, None, "Denied Project")
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_PROJECT,
            allowed=False,
            project_id=project.id,
        )

        project_ids = await permission_service.get_user_accessible_project_ids(
            test_user.id
        )
        assert project_ids == []

    async def test_get_user_accessible_team_ids_filters_actions(
        self,
        permission_service: PermissionService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        team_view = await _create_team(db_session, test_user_2)
        team_manage = await _create_team(db_session, test_user_2)
        team_denied = await _create_team(db_session, test_user_2)

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=True,
            team_id=team_view.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.MANAGE_TEAM,
            allowed=True,
            team_id=team_manage.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.VIEW_TEAM,
            allowed=False,
            team_id=team_denied.id,
        )

        team_ids = await permission_service.get_user_accessible_team_ids(
            test_user.id, actions=TeamActions.VIEW_TEAM
        )
        assert set(team_ids) == {team_view.id}

    async def test_get_permissions_requires_scope(
        self, permission_service: PermissionService
    ) -> None:
        with pytest.raises(
            InvalidScopeError,
            match="At least one of user_id, team_id, project_id must be provided.",
        ):
            await permission_service.get_permissions()

    async def test_nonexistent_ids_have_no_permissions_or_access(
        self, permission_service: PermissionService
    ) -> None:
        missing_user_id = uuid4()
        missing_team_id = uuid4()
        missing_project_id = uuid4()

        team_permissions = await permission_service.get_permissions(
            user_id=missing_user_id, team_id=missing_team_id
        )
        assert team_permissions.data == []

        project_permissions = await permission_service.get_permissions(
            user_id=missing_user_id, project_id=missing_project_id
        )
        assert project_permissions.data == []

        assert (
            await permission_service.has_permission(
                missing_user_id, TeamActions.VIEW_TEAM, team_id=missing_team_id
            )
            is False
        )
        with pytest.raises(DBNotFoundError):
            assert (
                await permission_service.has_permission(
                    missing_user_id,
                    ProjectActions.VIEW_PROJECT,
                    project_id=missing_project_id,
                )
                is False
            )

        accessible_projects = await permission_service.get_user_accessible_project_ids(
            missing_user_id
        )
        assert accessible_projects == []

        accessible_teams = await permission_service.get_user_accessible_team_ids(
            missing_user_id
        )
        assert accessible_teams == []
