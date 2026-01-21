from typing import List
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Project
from sqlalchemy.ext.asyncio import AsyncSession


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)

    async def get_projects_by_team(self, team_id: UUID_TYPE) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.team_id == team_id)

    async def get_projects_by_ids(self, project_ids: List[UUID_TYPE]) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.id.in_(project_ids))
