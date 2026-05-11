from typing import List
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import Project, Team, TeamMember
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ProjectRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)

    def _load_options(self, full_load: bool) -> list:
        if not full_load:
            return []
        return [
            selectinload(Project.owner),
            selectinload(Project.experiments),
            selectinload(Project.hypotheses),
            selectinload(Project.team),
        ]

    async def get_project_by_id(
        self, project_id: UUID_TYPE, full_load: bool = True
    ) -> Project | None:
        filters = [Project.id == project_id]
        return await self.advanced_alchemy_repository.get_one_or_none(
            *filters, load=self._load_options(full_load)
        )

    async def get_projects_by_ids(
        self,
        project_ids: List[UUID_TYPE],
        full_load: bool = True,
        list_options: ListOptions | None = None,
    ) -> Page[Project]:
        if not project_ids:
            return Page(data=[], has_next=False, total=0)
        filters = [Project.id.in_(project_ids)]
        return await self.list(
            *filters,
            order_by=Project.created_at.desc(),
            load=self._load_options(full_load),
            list_options=list_options,
        )

    async def get_projects_by_team(
        self, team_id: UUID_TYPE
    ) -> List[Project]:
        filters = [Project.team_id == team_id]
        return await self.advanced_alchemy_repository.list(
            *filters, load=[selectinload(Project.experiments)]
        )

    async def get_project_for_member_list(self, project_id: UUID_TYPE) -> Project | None:
        load = [
            selectinload(Project.owner),
            selectinload(Project.team)
            .selectinload(Team.owner),
            selectinload(Project.team)
            .selectinload(Team.member_links)
            .selectinload(TeamMember.user),
        ]
        return await self.advanced_alchemy_repository.get_one_or_none(
            Project.id == project_id, load=load
        )
