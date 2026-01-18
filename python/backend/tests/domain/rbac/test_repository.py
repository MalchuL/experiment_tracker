import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.error import InvalidScopeError
from domain.rbac.permissions.team import TeamActions
from domain.rbac.repository import PermissionRepository
from models import Permission, Project, Team, User


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
