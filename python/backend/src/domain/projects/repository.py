from typing import List
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Project
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from advanced_alchemy.repository.typing import OrderingPair
from domain.rbac.permissions import ProjectActions
from domain.rbac.repository import PermissionRepository
from lib.protocols.user_protocol import UserProtocol


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)
        self.permission_repository = PermissionRepository(db, auto_commit=False)

    async def get_accessible_projects(
        self,
        user: UserProtocol,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
        sort_by: OrderingPair | None = None,
        full_load: bool = True,
    ) -> List[Project]:
        permission_project_ids = (
            await self.permission_repository.get_user_accessible_projects_ids(
                user.id, actions=actions
            )
        )
        if not permission_project_ids:
            return []

        if full_load:
            options = [
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            ]
        else:
            options = []

        return await self.advanced_alchemy_repository.list(
            Project.id.in_(permission_project_ids), load=options, order_by=sort_by
        )

    async def get_project_if_accessible(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
        full_load: bool = True,
    ) -> Project | None:
        if full_load:
            options = [
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            ]
        else:
            options = []
        if await self.is_user_accessible_project(user, project_id, actions=actions):
            if full_load:
                return await self.advanced_alchemy_repository.get_one_or_none(
                    Project.id == project_id, load=options
                )
            return await self.advanced_alchemy_repository.get_one_or_none(
                Project.id == project_id
            )
        return None

    async def is_user_accessible_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        actions: list[str] | str | None = ProjectActions.VIEW_PROJECT,
    ) -> bool:
        return await self.permission_repository.is_user_accessible_project(
            user.id, project_id, actions=actions
        )

    async def get_projects_by_team(self, team_id: UUID_TYPE) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.team_id == team_id)

    async def get_projects_by_ids(self, project_ids: List[UUID_TYPE]) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.id.in_(project_ids))
