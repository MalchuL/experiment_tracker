from typing import List
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from models import Metric
from sqlalchemy.ext.asyncio import AsyncSession
from lib.types import UUID_TYPE
from sqlalchemy.orm import selectinload


class MetricRepository(BaseRepository[Metric]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)

    async def get_metrics_by_experiment(
        self,
        experiment_id: UUID_TYPE | list[UUID_TYPE],
        full_load: bool = False,
        list_options: ListOptions | None = None,
    ) -> Page[Metric]:
        if isinstance(experiment_id, (list, tuple)):
            scope = Metric.experiment_id.in_(experiment_id)
        else:
            scope = Metric.experiment_id == experiment_id
        load = [selectinload(Metric.experiment)] if full_load else []
        return await self.list(
            scope,
            order_by=Metric.created_at.desc(),
            load=load or None,
            list_options=list_options,
        )
