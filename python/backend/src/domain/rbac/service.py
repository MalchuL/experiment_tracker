# services/permission_service.py
from collections import defaultdict
from uuid import UUID
from typing import Dict, List, Optional

from domain.projects.repository import ProjectRepository
from domain.rbac.error import InvalidScopeError
from domain.rbac.permissions.project import role_to_project_permissions
from domain.rbac.permissions.team import role_to_team_permissions
from models import Permission, Role

from .repository import PermissionRepository
from .dto import PermissionDTO, PermissionListDTO
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionService:
    """Service for RBAC permissions and role-based grants.

    Team member roles generate both team-scoped and project-scoped permissions.
    By default, commits are not done automatically.

    Args:
        db: The database session.
        permission_repository: The permission repository.
        project_repository: The project repository.
        auto_commit: Whether to commit automatically.
    """

    def __init__(
        self,
        db: AsyncSession,
        permission_repository: PermissionRepository,
        project_repository: ProjectRepository,
        auto_commit: bool = False,
    ):
        """Initialize permission service with repositories and commit policy.

        Args:
            db: Async database session used for optional commits.
            permission_repository: Repository for permission rows.
            project_repository: Repository used to resolve project/team fallback.
            auto_commit: When ``True``, mutating helpers commit after writing.
        """
        self.db = db
        self.repo = permission_repository
        self.project_repo = project_repository
        self.auto_commit = auto_commit

    async def add_permission(
        self,
        user_id: UUID,
        action: str,
        allowed: bool = True,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> None:
        """Create a single permission row.

        Args:
            user_id: User receiving the permission.
            action: Permission action string.
            allowed: Whether the action is granted or explicitly denied.
            team_id: Optional team scope.
            project_id: Optional project scope.

        Returns:
            None: The row is created; commit is controlled by ``auto_commit``.
        """
        await self.repo.create_permission(
            Permission(
                user_id=user_id,
                action=action,
                allowed=allowed,
                team_id=team_id,
                project_id=project_id,
            )
        )
        if self.auto_commit:
            await self.db.commit()

    async def get_permissions(
        self,
        user_id: UUID | None = None,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
        actions: list[str] | str | None = None,
    ) -> PermissionListDTO:
        """Fetch permission rows matching optional filters.

        Args:
            user_id: Optional user filter.
            team_id: Optional team-scope filter.
            project_id: Optional project-scope filter.
            actions: Optional action or actions to include.

        Returns:
            PermissionListDTO: DTO wrapper containing matching permission rows.
        """
        permissions = await self.repo.get_permissions(
            user_id=user_id,
            team_id=team_id,
            project_id=project_id,
            actions=actions,
        )
        return PermissionListDTO(
            data=[
                PermissionDTO(
                    user_id=permission.user_id,
                    action=permission.action,
                    allowed=permission.allowed,
                    team_id=permission.team_id,
                    project_id=permission.project_id,
                )
                for permission in permissions
            ]
        )

    async def has_permission(
        self,
        user_id: UUID,
        actions: str | list[str] | None,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> bool:
        """Check whether a user is allowed to perform an action.

        Args:
            user_id: User whose access is checked.
            actions: Action or actions to require. ``None`` delegates to repository
                behavior for unfiltered permission lookup.
            team_id: Optional team scope. Mutually exclusive with ``project_id``.
            project_id: Optional project scope. Mutually exclusive with ``team_id``.

        Returns:
            bool: ``True`` if any matching permission allows the action.

        Raises:
            InvalidScopeError: If both ``team_id`` and ``project_id`` are provided.

        Resolution order project_id:
        1) If project_id is provided, check project-scoped permissions first.
           - If any project permissions exist for the action, they decide the result.
           - If no project permissions exist, and the project belongs to a team,
             fall back to team-scoped permissions for that team.
        2) If project_id is not provided, check only team-scoped permissions.

        Resolution order team_id:
        1) If team_id is provided, check team-scoped permissions first.
           - If any team permissions exist for the action, they decide the result.
        """
        if project_id is not None and team_id is not None:
            raise InvalidScopeError(
                "Only one of project_id or team_id can be provided."
            )
        if project_id is None:
            permissions = await self.repo.get_permissions(
                user_id=user_id, team_id=team_id, project_id=None, actions=actions
            )
            return any(permission.allowed for permission in permissions)

        project_permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id, actions=actions
        )
        if project_permissions:
            return any(permission.allowed for permission in project_permissions)

        project = await self.project_repo.get_project_by_id(
            project_id, full_load=False
        )
        if project is None:
            return False
        if project.team_id is None:
            return False

        team_permissions = await self.repo.get_permissions(
            user_id=user_id, team_id=project.team_id, actions=actions
        )
        return any(permission.allowed for permission in team_permissions)

    async def get_user_accessible_project_ids(
        self, user_id: UUID, actions: list[str] | str | None = None
    ) -> list[UUID]:
        """Return project ids accessible through direct or team permissions.

        Args:
            user_id: User whose accessible projects are requested.
            actions: Optional action or actions that must be allowed.

        Returns:
            list[UUID]: Project ids granted directly or inherited from team access.
        """
        project_ids = set(
            await self.repo.get_user_projects_exists_permissions_ids(
                user_id, actions=actions
            )
        )
        team_ids = await self.repo.get_user_accessible_teams_ids(
            user_id, actions=actions
        )
        for team_id in team_ids:
            projects = await self.project_repo.get_projects_by_team(team_id=team_id)
            project_ids.update(project.id for project in projects)
        return list(project_ids)

    async def get_user_accessible_team_ids(
        self, user_id: UUID, actions: list[str] | str | None = None
    ) -> list[UUID]:
        """Return team ids where the user has allowed permissions.

        Args:
            user_id: User whose teams are requested.
            actions: Optional action or actions that must be allowed.

        Returns:
            list[UUID]: Team ids matching the permission filter.
        """
        return await self.repo.get_user_accessible_teams_ids(user_id, actions=actions)

    # Team permissions
    async def add_user_to_team_permissions(
        self, user_id: UUID, team_id: UUID, role: Role
    ) -> None:
        """Grant team member permissions for a role.

        This creates both team permissions and project permissions so that
        team membership also grants project-level actions by default.

        Args:
            user_id: User receiving role permissions.
            team_id: Team scope for the permissions.
            role: Role whose team and project action map should be applied.

        Returns:
            None: Existing rows are updated or missing rows are created; commit is
            controlled by ``auto_commit``.
        """
        # Combine team and project permissions which is default behavior for team members
        team_permissions = role_to_team_permissions(role) | role_to_project_permissions(
            role
        )
        existing_permissions = await self.repo.get_permissions(
            user_id=user_id, team_id=team_id
        )
        existing_by_action = {
            permission.action: permission for permission in existing_permissions
        }
        for action, allowed in team_permissions.items():
            existing = existing_by_action.get(action)
            if existing is None:
                await self.repo.create_permission(
                    Permission(
                        user_id=user_id,
                        action=action,
                        allowed=allowed,
                        team_id=team_id,
                    )
                )
            else:
                existing.allowed = allowed
                await self.repo.update_permission(existing)
        if self.auto_commit:
            await self.db.commit()

    async def remove_user_from_team_permissions(
        self, user_id: UUID, team_id: UUID
    ) -> None:
        """Remove team-scoped permissions and project overrides for team projects.

        Args:
            user_id: User whose permissions are removed.
            team_id: Team being left or managed.

        Returns:
            None: Matching permission rows are deleted; commit is controlled by
            ``auto_commit``.
        """
        permissions = await self.repo.get_permissions(user_id=user_id, team_id=team_id)
        await self.repo.delete_permission(permissions)

        projects = await self.project_repo.get_projects_by_team(team_id=team_id)
        for project in projects:
            permissions = await self.repo.get_permissions(
                user_id=user_id, project_id=project.id
            )
            if permissions:
                await self.repo.delete_permission(permissions)
        if self.auto_commit:
            await self.db.commit()

    async def update_user_team_role_permissions(
        self, user_id: UUID, team_id: UUID, role: Role
    ) -> None:
        """Update existing team-scope permissions to match a role.

        Args:
            user_id: Team member being changed.
            team_id: Team scope.
            role: New role whose permission map should be applied.

        Returns:
            None: Existing permission rows are updated; commit is controlled by
            ``auto_commit``.
        """
        permissions = await self.repo.get_permissions(user_id=user_id, team_id=team_id)
        new_permissions = role_to_team_permissions(role) | role_to_project_permissions(
            role
        )
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.repo.update_permission(permission)

        if self.auto_commit:
            await self.db.commit()

    # Project permissions
    async def add_user_to_project_permissions(
        self, user_id: UUID, project_id: UUID, role: Role
    ) -> None:
        """Grant or replace project-scoped permissions for a role.

        Args:
            user_id: User receiving project permissions.
            project_id: Project scope.
            role: Role whose project action map should be applied.

        Returns:
            None: Existing rows are updated or missing rows are created; commit is
            controlled by ``auto_commit``.
        """
        project_permissions = role_to_project_permissions(role)
        existing_permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        existing_by_action = {
            permission.action: permission for permission in existing_permissions
        }
        for action, allowed in project_permissions.items():
            existing = existing_by_action.get(action)
            if existing is None:
                await self.repo.create_permission(
                    Permission(
                        user_id=user_id,
                        action=action,
                        allowed=allowed,
                        project_id=project_id,
                    ),
                )
            else:
                existing.allowed = allowed
                await self.repo.update_permission(existing)
        if self.auto_commit:
            await self.db.commit()

    async def remove_user_from_project_permissions(
        self, user_id: UUID, project_id: UUID
    ) -> None:
        """Remove all direct project-scoped permissions for a user.

        Args:
            user_id: User whose direct project permissions are removed.
            project_id: Project scope.

        Returns:
            None: Matching permission rows are deleted; commit is controlled by
            ``auto_commit``.
        """
        permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        await self.repo.delete_permission(permissions)
        if self.auto_commit:
            await self.db.commit()

    async def update_user_project_role_permissions(
        self, user_id: UUID, project_id: UUID, role: Role
    ) -> None:
        """Update existing project-scoped permissions to match a role.

        Args:
            user_id: User whose project role is changing.
            project_id: Project scope.
            role: New role whose project action map should be applied.

        Returns:
            None: Existing permission rows are updated; commit is controlled by
            ``auto_commit``.
        """
        permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        new_permissions = role_to_project_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.repo.update_permission(permission)
        if self.auto_commit:
            await self.db.commit()
