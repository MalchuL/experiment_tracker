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
    """

    def __init__(
        self,
        db: AsyncSession,
        permission_repository: PermissionRepository,
        project_repository: ProjectRepository,
    ):
        """Initialize permission service with a database session."""
        self.db = db
        self.repo = permission_repository
        self.project_repo = project_repository

    async def add_permission(
        self,
        user_id: UUID,
        action: str,
        allowed: bool = True,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> None:
        """Create a new permission scoped to a team or project."""
        await self.repo.create_permission(
            Permission(
                user_id=user_id,
                action=action,
                allowed=allowed,
                team_id=team_id,
                project_id=project_id,
            )
        )
        await self.db.commit()

    async def get_permissions(
        self,
        user_id: UUID | None = None,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
        actions: list[str] | str | None = None,
    ) -> PermissionListDTO:
        """Fetch permissions matching the provided filters."""
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
            user_id (UUID): The id of the user.
            actions (str | list[str] | None): The actions to grant permission for.
            team_id (UUID | None, optional): The id of the team. Defaults to None.
            project_id (UUID | None, optional): The id of the project. Defaults to None.
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

        project = await self.project_repo.get_by_id(project_id)
        if project.team_id is None:
            return False

        team_permissions = await self.repo.get_permissions(
            user_id=user_id, team_id=project.team_id, actions=actions
        )
        return any(permission.allowed for permission in team_permissions)

    async def get_user_accessible_project_ids(
        self, user_id: UUID, actions: list[str] | str | None = None
    ) -> list[UUID]:
        """Return project ids accessible via permissions or team permissions."""
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
        """Return team ids where the user has allowed permissions."""
        return await self.repo.get_user_accessible_teams_ids(user_id, actions=actions)

    # Team permissions
    async def add_user_to_team_permissions(
        self, user_id: UUID, team_id: UUID, role: Role
    ) -> None:
        """Grant team member permissions for a role.

        This creates both team permissions and project permissions so that
        team membership also grants project-level actions by default.
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
        await self.db.commit()

    async def remove_user_from_team_permissions(
        self, user_id: UUID, team_id: UUID
    ) -> None:
        """Remove all team-scoped permissions and related project permissions."""
        permissions = await self.repo.get_permissions(user_id=user_id, team_id=team_id)
        await self.repo.delete_permission(permissions)

        projects = await self.project_repo.get_projects_by_team(team_id=team_id)
        for project in projects:
            permissions = await self.repo.get_permissions(
                user_id=user_id, project_id=project.id
            )
            if permissions:
                await self.repo.delete_permission(permissions)
        await self.db.commit()

    async def update_user_team_role_permissions(
        self, user_id: UUID, team_id: UUID, role: Role
    ) -> None:
        """Update team and project permissions for a team member role."""
        permissions = await self.repo.get_permissions(user_id=user_id, team_id=team_id)
        new_permissions = role_to_team_permissions(role) | role_to_project_permissions(
            role
        )
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.repo.update_permission(permission)

        await self.db.commit()

    # Project permissions
    async def add_user_to_project_permissions(
        self, user_id: UUID, project_id: UUID, role: Role
    ) -> None:
        """Grant project-scoped permissions for a role."""
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
        await self.db.commit()

    async def remove_user_from_project_permissions(
        self, user_id: UUID, project_id: UUID
    ) -> None:
        """Remove all project-scoped permissions for a user."""
        permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        await self.repo.delete_permission(permissions)
        await self.db.commit()

    async def update_user_project_role_permissions(
        self, user_id: UUID, project_id: UUID, role: Role
    ) -> None:
        """Update project-scoped permissions for a user role."""
        permissions = await self.repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        new_permissions = role_to_project_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.repo.update_permission(permission)
        await self.db.commit()
