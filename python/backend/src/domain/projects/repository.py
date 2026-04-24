from typing import List
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import Project
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
        return await self.advanced_alchemy_repository.get_one_or_none(
            Project.id == project_id, load=self._load_options(full_load)
        )

    async def get_projects_by_ids(
        self,
        project_ids: List[UUID_TYPE],
        full_load: bool = True,
        list_options: ListOptions | None = None,
    ) -> Page[Project]:
        if not project_ids:
            return Page(data=[], has_next=False, total=0)
        return await self.list(
            Project.id.in_(project_ids),
            load=self._load_options(full_load),
            list_options=list_options,
        )

    async def get_projects_by_team(self, team_id: UUID_TYPE) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.team_id == team_id)
