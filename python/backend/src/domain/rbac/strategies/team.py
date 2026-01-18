from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.repository import ProjectRepository
from domain.rbac.permissions.team import role_to_team_permissions
from domain.rbac.repository import PermissionRepository
from domain.rbac.strategies.project import ProjectRbacStrategy
from domain.team.teams.repository import TeamRepository
from models import Permission, Team, TeamRole


class TeamRbacStrategy:
    def __init__(self, db: AsyncSession, auto_commit: bool = False):
        self.db = db
        self.auto_commit = auto_commit
        self.project_repository = ProjectRepository(db)
        self.team_repository = TeamRepository(db)
        self.permission_repo = PermissionRepository(db, auto_commit=auto_commit)
        self.project_rbac_strategy = ProjectRbacStrategy(db, auto_commit=False)

    def _normalize_actions(self, actions: List[str] | str | None) -> List[str] | None:
        if actions is None:
            return None
        if isinstance(actions, str):
            return [actions]
        return actions

    async def add_team_member_permissions(
        self, team_id: UUID, user_id: UUID, role: TeamRole
    ) -> None:
        team_permissions = role_to_team_permissions(role)
        for action, allowed in team_permissions.items():
            await self.permission_repo.create_permission(
                Permission(
                    user_id=user_id,
                    action=action,
                    allowed=allowed,
                    team_id=team_id,
                )
            )
        projects = await self.project_repository.get_projects_by_team(team_id)
        for project in projects:
            await self.project_rbac_strategy.add_project_member_permissions(
                project.id, user_id, role
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

        projects = await self.project_repository.get_projects_by_team(team_id)
        for project in projects:
            await self.project_rbac_strategy.remove_project_member_permissions(
                project.id, user_id
            )
        if self.auto_commit:
            await self.db.commit()

    async def update_team_member_role_permissions(
        self, team_id: UUID, user_id: UUID, role: TeamRole
    ) -> None:
        permissions = await self.permission_repo.get_permissions(
            user_id=user_id, team_id=team_id
        )
        new_permissions = role_to_team_permissions(role)
        for permission in permissions:
            permission.allowed = new_permissions[permission.action]
            await self.permission_repo.update_permission(permission)

        projects = await self.project_repository.get_projects_by_team(team_id)
        for project in projects:
            await self.project_rbac_strategy.update_project_member_role_permissions(
                project.id, user_id, role
            )
        if self.auto_commit:
            await self.db.commit()

    async def get_user_accessible_teams(
        self, user_id: UUID, actions: List[str] | str | None = None
    ) -> List[Team]:

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
        team_ids = [permission_id for permission_id in permissions_ids]
        return await self.team_repository.get_teams_by_ids(team_ids)
