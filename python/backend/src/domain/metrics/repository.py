from domain.projects.repository import ProjectRepository
from lib.protocols.user_protocol import UserProtocol
from lib.db.base_repository import BaseRepository
from models import Metric
from sqlalchemy.ext.asyncio import AsyncSession
from lib.types import UUID_TYPE
from domain.experiments.repository import ExperimentRepository
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class MetricRepository(BaseRepository[Metric]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)

    async def get_metrics_by_experiment(
        self,
        experiment_id: UUID_TYPE | list[UUID_TYPE],
        full_load: bool = False,
    ) -> List[Metric]:
        conditions = []
        if isinstance(experiment_id, (list, tuple)):
            conditions.append(Metric.experiment_id.in_(experiment_id))
        else:
            conditions.append(Metric.experiment_id == experiment_id)
        if full_load:
            load = [selectinload(Metric.experiment)]
        else:
            load = []
        metrics = await self.advanced_alchemy_repository.list(
            *conditions,
            order_by=Metric.created_at.desc(),
            load=load,
        )
        return metrics
