# services/permission_service.py
from collections import defaultdict
from uuid import UUID
from typing import Dict, List, Optional

from domain.rbac.strategies.project import ProjectRbacStrategy
from domain.rbac.strategies.team import TeamRbacStrategy
from models import Permission, TeamRole

from .repository import PermissionRepository
from .dto import PermissionDTO, PermissionListDTO
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionService:

    def __init__(self, db: AsyncSession, auto_commit: bool = True):
        self.db = db
        self.repo = PermissionRepository(db, auto_commit=auto_commit)
        self.auto_commit = auto_commit

    async def add_permission(
        self,
        user_id: UUID,
        action: str,
        allowed: bool = True,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> None:
        """Create a new permission.

        Args:
            user_id (UUID): The id of the user.
            action (str): The action to grant permission for.
            allowed (bool, optional): Whether the permission is granted. Defaults to True.
            team_id (UUID | None, optional): The id of the team. Defaults to None.
            project_id (UUID | None, optional): The id of the project. Defaults to None.
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

    async def get_permissions(
        self,
        user_id: UUID | None = None,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
        actions: list[str] | str | None = None,
    ) -> PermissionListDTO:
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
        action: str,
        team_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> bool:
        permissions = await self.repo.get_permissions(
            user_id=user_id, team_id=team_id, project_id=project_id, actions=action
        )
        return any(permission.allowed for permission in permissions)

    # Team permissions
    async def add_user_to_team_permissions(
        self, user_id: UUID, team_id: UUID, role: TeamRole
    ) -> None:
        team_strategy = TeamRbacStrategy(self.db, auto_commit=self.auto_commit)
        await team_strategy.add_team_member_permissions(team_id, user_id, role)

    async def remove_user_from_team_permissions(
        self, user_id: UUID, team_id: UUID
    ) -> None:
        team_strategy = TeamRbacStrategy(self.db, auto_commit=self.auto_commit)
        await team_strategy.remove_team_member_permissions(team_id, user_id)

    async def update_user_team_role_permissions(
        self, user_id: UUID, team_id: UUID, role: TeamRole
    ) -> None:
        team_strategy = TeamRbacStrategy(self.db, auto_commit=self.auto_commit)
        await team_strategy.update_team_member_role_permissions(team_id, user_id, role)

    # Project permissions
    async def add_user_to_project_permissions(
        self, user_id: UUID, project_id: UUID, role: TeamRole
    ) -> None:
        project_strategy = ProjectRbacStrategy(self.db, auto_commit=self.auto_commit)
        await project_strategy.add_project_member_permissions(project_id, user_id, role)

    async def remove_user_from_project_permissions(
        self, user_id: UUID, project_id: UUID
    ) -> None:
        project_strategy = ProjectRbacStrategy(self.db, auto_commit=self.auto_commit)
        await project_strategy.remove_project_member_permissions(project_id, user_id)

    async def update_user_project_role_permissions(
        self, user_id: UUID, project_id: UUID, role: TeamRole
    ) -> None:
        project_strategy = ProjectRbacStrategy(self.db, auto_commit=self.auto_commit)
        await project_strategy.update_project_member_role_permissions(
            project_id, user_id, role
        )

    async def commit(self) -> None:
        await self.db.commit()
