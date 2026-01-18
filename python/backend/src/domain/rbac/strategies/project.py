from typing import List
from domain.rbac.permissions.project import role_to_project_permissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from domain.rbac.repository import PermissionRepository
from domain.projects.repository import ProjectRepository
from models import Permission, Project, TeamRole


class ProjectRbacStrategy:
    def __init__(self, db: AsyncSession, auto_commit: bool = False):
        self.db = db
        self.permission_repo = PermissionRepository(db, auto_commit=auto_commit)
        self.project_repository = ProjectRepository(db)
        self.auto_commit = auto_commit

    @staticmethod
    def _normalize_actions(actions: List[str] | str | None) -> List[str] | None:
        if actions is None:
            return None
        if isinstance(actions, str):
            return [actions]
        return actions

    async def add_project_member_permissions(
        self, project_id: UUID, user_id: UUID, role: TeamRole
    ) -> None:
        project_permissions = role_to_project_permissions(role)
        for action, allowed in project_permissions.items():
            await self.permission_repo.create_permission(
                Permission(
                    user_id=user_id,
                    action=action,
                    allowed=allowed,
                    project_id=project_id,
                ),
            )

    async def remove_project_member_permissions(
        self, project_id: UUID, user_id: UUID
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        await self.permission_repo.delete_permission(permissions)

    async def update_project_member_role_permissions(
        self, project_id: UUID, user_id: UUID, role: TeamRole
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, project_id=project_id
        )
        new_permissions = role_to_project_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.permission_repo.update_permission(permission)

    async def get_user_accessible_projects(
        self, user_id: UUID, actions: List[str] | str | None = None
    ) -> List[Project]:
        conditions = []
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

        project_ids = [permission_id for permission_id in permissions_ids]
        return await self.project_repository.get_projects_by_ids(project_ids)
