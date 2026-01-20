import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.permissions import ProjectActions, TeamActions
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from models import Project, Team, User


async def _create_team(db_session: AsyncSession, owner: User) -> Team:
    team = Team(
        id=None,
        name="Wrapper Team",
        description="RBAC wrapper team",
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
        description="Wrapper project",
        owner_id=owner.id,
        team_id=team.id if team else None,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestPermissionChecker:
    async def test_project_action_wrappers(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user, None, "Project A")
        permission_service = PermissionService(db_session, auto_commit=True)

        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_PROJECT,
            allowed=True,
            project_id=project.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.DELETE_PROJECT,
            allowed=False,
            project_id=project.id,
        )

        checker = PermissionChecker(db_session)
        assert (await checker.can_edit_project(test_user.id, project.id)) is True
        assert (await checker.can_delete_project(test_user.id, project.id)) is False

    async def test_team_action_wrappers(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        team = await _create_team(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)

        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.MANAGE_TEAM,
            allowed=True,
            team_id=team.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=TeamActions.DELETE_TEAM,
            allowed=False,
            team_id=team.id,
        )

        checker = PermissionChecker(db_session)
        assert await checker.can_manage_team(test_user.id, team.id) is True
        assert await checker.can_delete_team(test_user.id, team.id) is False
