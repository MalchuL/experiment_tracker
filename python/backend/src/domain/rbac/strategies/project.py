from typing import List
from domain.rbac.permissions.project import role_to_project_permissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from domain.rbac.repository import PermissionRepository
from models import Permission, Role


class ProjectRbacStrategy:
    def __init__(self, db: AsyncSession, auto_commit: bool = False):
        self.db = db
        self.permission_repo = PermissionRepository(db, auto_commit=auto_commit)
        self.auto_commit = auto_commit

    @staticmethod
    def _normalize_actions(actions: List[str] | str | None) -> List[str] | None:
        if actions is None:
            return None
        if isinstance(actions, str):
            return [actions]
        return actions

    async def add_project_member_permissions(
        self, project_id: UUID, user_id: UUID, role: Role
    ) -> None:
        project_permissions = role_to_project_permissions(role)
        existing_permissions = await self.permission_repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        existing_by_action = {
            permission.action: permission for permission in existing_permissions
        }
        for action, allowed in project_permissions.items():
            existing = existing_by_action.get(action)
            if existing is None:
                await self.permission_repo.create_permission(
                    Permission(
                        user_id=user_id,
                        action=action,
                        allowed=allowed,
                        project_id=project_id,
                    ),
                )
            else:
                existing.allowed = allowed
                await self.permission_repo.update_permission(existing)

    async def remove_project_member_permissions(
        self, project_id: UUID, user_id: UUID
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        await self.permission_repo.delete_permission(permissions)

    async def update_project_member_role_permissions(
        self, project_id: UUID, user_id: UUID, role: Role
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        new_permissions = role_to_project_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.permission_repo.update_permission(permission)

    async def get_user_accessible_projects_ids(
        self, user_id: UUID, actions: List[str] | str | None = None
    ) -> List[UUID]:
        conditions = [Permission.allowed.is_(True)]
        normalized_actions = self._normalize_actions(actions)
        if normalized_actions is not None:
            conditions.append(Permission.action.in_(normalized_actions))
        permissions_ids = await self.permission_repo.advanced_alchemy_repository.list(
            Permission.user_id == user_id,
            Permission.project_id.is_not(None),
            *conditions,
            statement=select(Permission.project_id).distinct(),
        )
        if not permissions_ids:
            return []

        return [permission_id for permission_id in permissions_ids]

    async def is_user_accessible_project(
        self,
        user_id: UUID,
        project_id: UUID,
        actions: List[str] | str | None = None,
    ) -> bool:
        conditions = [
            Permission.user_id == user_id,
            Permission.project_id == project_id,
            Permission.allowed.is_(True),
        ]
        normalized_actions = self._normalize_actions(actions)
        if normalized_actions is not None:
            conditions.append(Permission.action.in_(normalized_actions))
        result = await self.permission_repo.advanced_alchemy_repository.list(
            *conditions,
            statement=select(Permission.project_id).distinct(),
        )
        return len(result) > 0
