import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.deps import build_permission_checker
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import (
    InactiveUserPermissionChecker,
    PermissionChecker,
    SuperuserPermissionChecker,
)
from models import Project, User


async def _create_project(db_session: AsyncSession, owner: User) -> Project:
    project = Project(
        id=None,
        name="Superuser test project",
        description="",
        owner_id=owner.id,
        team_id=None,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


class TestSuperuserPermissionChecker:
    async def test_superuser_checker_grants_without_permissions(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        normal = build_permission_checker(test_user_2, db_session, permission_service)
        test_user_2.is_superuser = True
        elevated = build_permission_checker(test_user_2, db_session, permission_service)

        assert isinstance(normal, PermissionChecker)
        assert not isinstance(normal, SuperuserPermissionChecker)
        assert isinstance(elevated, SuperuserPermissionChecker)

        assert await normal.can_view_project(test_user_2.id, project.id) is False
        assert await elevated.can_view_project(test_user_2.id, project.id) is True
        assert await elevated.can_delete_project(test_user_2.id, project.id) is True

    async def test_superuser_checker_rejects_null_ids(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        permission_service = PermissionService(db_session, auto_commit=True)
        test_user.is_superuser = True
        checker = build_permission_checker(test_user, db_session, permission_service)
        assert await checker.can_view_project(test_user.id, None) is False
        assert await checker.can_view_project(None, test_user.id) is False

    async def test_build_permission_checker_uses_normal_for_non_superuser(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        permission_service = PermissionService(db_session, auto_commit=True)
        checker = build_permission_checker(test_user, db_session, permission_service)
        assert type(checker) is PermissionChecker

    async def test_inactive_checker_denies_even_with_permissions(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user_2.id,
            project_id=project.id,
            action=ProjectActions.VIEW_PROJECT,
        )
        test_user_2.is_active = False
        checker = build_permission_checker(test_user_2, db_session, permission_service)

        assert isinstance(checker, InactiveUserPermissionChecker)
        assert await checker.can_view_project(test_user_2.id, project.id) is False

    async def test_inactive_superuser_is_denied(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        test_user_2.is_superuser = True
        test_user_2.is_active = False
        checker = build_permission_checker(test_user_2, db_session, permission_service)

        assert isinstance(checker, InactiveUserPermissionChecker)
        assert await checker.can_view_project(test_user_2.id, project.id) is False
