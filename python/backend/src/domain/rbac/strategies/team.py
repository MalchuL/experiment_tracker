from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.permissions.team import role_to_team_permissions
from domain.rbac.repository import PermissionRepository
from domain.rbac.strategies.project import ProjectRbacStrategy
from models import Permission, Project, Role


class TeamRbacStrategy:
    def __init__(self, db: AsyncSession, auto_commit: bool = False):
        self.db = db
        self.auto_commit = auto_commit
        self.permission_repo = PermissionRepository(db, auto_commit=auto_commit)
        self.project_rbac_strategy = ProjectRbacStrategy(db, auto_commit=False)

    def _normalize_actions(self, actions: List[str] | str | None) -> List[str] | None:
        if actions is None:
            return None
        if isinstance(actions, str):
            return [actions]
        return actions

    async def add_team_member_permissions(
        self, team_id: UUID, user_id: UUID, role: Role
    ) -> None:
        team_permissions = role_to_team_permissions(role)
        existing_permissions = await self.permission_repo.get_permissions(
            user_id=user_id, team_id=team_id
        )
        existing_by_action = {
            permission.action: permission for permission in existing_permissions
        }
        for action, allowed in team_permissions.items():
            existing = existing_by_action.get(action)
            if existing is None:
                await self.permission_repo.create_permission(
                    Permission(
                        user_id=user_id,
                        action=action,
                        allowed=allowed,
                        team_id=team_id,
                    )
                )
            else:
                existing.allowed = allowed
                await self.permission_repo.update_permission(existing)
        project_ids = await self._get_team_project_ids(team_id)
        for project_id in project_ids:
            await self.project_rbac_strategy.add_project_member_permissions(
                project_id, user_id, role
            )
        if self.auto_commit:
            await self.db.commit()

    async def remove_team_member_permissions(
        self, team_id: UUID, user_id: UUID
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, team_id=team_id
        )
        await self.permission_repo.delete_permission(permissions)

        project_ids = await self._get_team_project_ids(team_id)
        for project_id in project_ids:
            await self.project_rbac_strategy.remove_project_member_permissions(
                project_id, user_id
            )
        if self.auto_commit:
            await self.db.commit()

    async def update_team_member_role_permissions(
        self, team_id: UUID, user_id: UUID, role: Role
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, team_id=team_id
        )
        new_permissions = role_to_team_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.permission_repo.update_permission(permission)

        project_ids = await self._get_team_project_ids(team_id)
        for project_id in project_ids:
            await self.project_rbac_strategy.update_project_member_role_permissions(
                project_id, user_id, role
            )
        if self.auto_commit:
            await self.db.commit()

    async def get_user_accessible_teams(
        self, user_id: UUID, actions: List[str] | str | None = None
    ) -> List[UUID]:
        conditions = []
        normalized_actions = self._normalize_actions(actions)
        if normalized_actions is not None:
            conditions.append(Permission.action.in_(normalized_actions))
        permissions_ids = await self.permission_repo.advanced_alchemy_repository.list(
            Permission.user_id == user_id,
            Permission.team_id.is_not(None),
            *conditions,
            statement=select(Permission.team_id).distinct(),
        )
        if not permissions_ids:
            return []
        return [permission_id for permission_id in permissions_ids]

    async def _get_team_project_ids(self, team_id: UUID) -> List[UUID]:
        result = await self.db.execute(
            select(Project.id).where(Project.team_id == team_id)
        )
        return list(result.scalars().all())
