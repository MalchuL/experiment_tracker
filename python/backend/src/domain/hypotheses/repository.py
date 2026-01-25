from typing import Any, List
from advanced_alchemy.filters import LimitOffset
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Hypothesis
from sqlalchemy.ext.asyncio import AsyncSession


class HypothesisRepository(BaseRepository[Hypothesis]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Hypothesis)

    async def get_hypotheses_by_project(
        self, project_id: UUID_TYPE | list[UUID_TYPE], limit: int | None = None
    ) -> List[Hypothesis]:
        conditions: list[Any] = []
        if isinstance(project_id, (list, tuple)):
            conditions.append(Hypothesis.project_id.in_(project_id))
        else:
            conditions.append(Hypothesis.project_id == project_id)
        if limit:
            conditions.append(LimitOffset(offset=0, limit=limit))
        hypotheses = await self.advanced_alchemy_repository.list(
            *conditions,
            order_by=Hypothesis.created_at.desc(),
        )
        return hypotheses
