from typing import List
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import Hypothesis
from sqlalchemy.ext.asyncio import AsyncSession


class HypothesisRepository(BaseRepository[Hypothesis]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Hypothesis)

    async def get_hypotheses_by_project(
        self,
        project_id: UUID_TYPE | list[UUID_TYPE],
        list_options: ListOptions | None = None,
    ) -> Page[Hypothesis]:
        if isinstance(project_id, (list, tuple)):
            scope = Hypothesis.project_id.in_(project_id)
        else:
            scope = Hypothesis.project_id == project_id
        return await self.list(
            scope,
            order_by=Hypothesis.created_at.desc(),
            list_options=list_options,
        )
