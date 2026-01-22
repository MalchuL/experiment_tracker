from typing import List
from advanced_alchemy.filters import LimitOffset
from lib.db.base_repository import BaseRepository, ListOptions
from lib.types import UUID_TYPE
from models import Experiment
from sqlalchemy.ext.asyncio import AsyncSession

from lib.protocols.user_protocol import UserProtocol


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Experiment)

    async def get_user_experiments(
        self, user: UserProtocol, list_options: ListOptions | None = None
    ) -> List[Experiment]:
        list_conditions = []
        if list_options:
            limit_offset = LimitOffset(
                offset=list_options.offset, limit=list_options.limit
            )
            list_conditions.append(limit_offset)

        result = await self.advanced_alchemy_repository.list(
            Experiment.started_by == user.id,
            *list_conditions,
            order_by=Experiment.created_at.desc(),
        )
        return result

    async def get_experiments_by_project(
        self, project_id: UUID_TYPE
    ) -> List[Experiment]:
        experiments = await self.advanced_alchemy_repository.list(
            Experiment.project_id == project_id,
        )
        return experiments
