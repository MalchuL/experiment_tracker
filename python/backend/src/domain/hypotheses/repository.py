from typing import List
import uuid
from advanced_alchemy.filters import LimitOffset
from lib.db.base_repository import BaseRepository, ListOptions
from lib.types import UUID_TYPE
from models import Hypothesis, Project
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.repository import ProjectRepository
from lib.protocols.user_protocol import UserProtocol
from domain.rbac.defaults import team_roles_with_permission
from domain.rbac.permissions import PROJECT_VIEW
from models import (
    Permission,
    Role,
    RoleAssignment,
    RBACScope,
    TeamMember,
    role_permissions,
)


class HypothesisRepository(BaseRepository[Hypothesis]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Hypothesis)
        self.project_repository = ProjectRepository(db)
        self.db = db

    def _project_role_subquery(self, user: UserProtocol):
        return (
            select(Role.scope_id)
            .select_from(RoleAssignment)
            .join(Role, RoleAssignment.role_id == Role.id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                RoleAssignment.user_id == user.id,
                Role.scope == RBACScope.PROJECT,
                Permission.key == PROJECT_VIEW,
            )
        )

    def _team_role_subquery(self, user: UserProtocol):
        return (
            select(Role.scope_id)
            .select_from(RoleAssignment)
            .join(Role, RoleAssignment.role_id == Role.id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                RoleAssignment.user_id == user.id,
                Role.scope == RBACScope.TEAM,
                Permission.key == PROJECT_VIEW,
            )
        )

    async def _get_user_team_ids_with_permission(
        self, user: UserProtocol, permission_key: str
    ) -> List[uuid.UUID]:
        allowed_roles = team_roles_with_permission(permission_key)
        if not allowed_roles:
            return []
        query = select(TeamMember.team_id).where(
            TeamMember.user_id == user.id, TeamMember.role.in_(allowed_roles)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_accessible_hypotheses(
        self, user: UserProtocol, list_options: ListOptions | None = None
    ) -> List[Hypothesis]:
        team_ids = await self._get_user_team_ids_with_permission(user, PROJECT_VIEW)
        project_role_subquery = self._project_role_subquery(user)
        team_role_subquery = self._team_role_subquery(user)
        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))
        conditions.append(Project.id.in_(project_role_subquery))
        conditions.append(Project.team_id.in_(team_role_subquery))
        list_conditions = []
        if list_options:
            limit_offset = LimitOffset(
                offset=list_options.offset, limit=list_options.limit
            )
            list_conditions.append(limit_offset)
        result = await self.advanced_alchemy_repository.list(
            or_(*conditions),
            *list_conditions,
            order_by=Hypothesis.created_at.desc(),
        )
        return result

    async def get_hypotheses_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[Hypothesis]:
        project = await self.project_repository.get_project_if_accessible(
            user, project_id
        )
        if not project:
            return []

        hypotheses = await self.advanced_alchemy_repository.list(
            Hypothesis.project_id == project_id,
            order_by=Hypothesis.created_at.desc(),
        )
        return hypotheses

    async def get_hypothesis_if_accessible(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> Hypothesis | None:
        team_ids = await self._get_user_team_ids_with_permission(user, PROJECT_VIEW)
        project_role_subquery = self._project_role_subquery(user)
        team_role_subquery = self._team_role_subquery(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))
        conditions.append(Project.id.in_(project_role_subquery))
        conditions.append(Project.team_id.in_(team_role_subquery))

        return await self.advanced_alchemy_repository.get_one_or_none(
            Hypothesis.id == hypothesis_id,
            or_(*conditions),
        )
