from domain.projects.repository import ProjectRepository, UserProtocol
from lib.db.base_repository import BaseRepository
from models import Metric
from sqlalchemy.ext.asyncio import AsyncSession
from lib.types import UUID_TYPE
from domain.experiments.repository import ExperimentRepository
from typing import List
from sqlalchemy import select


class MetricRepository(BaseRepository[Metric]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)
        self.experiment_repository = ExperimentRepository(db)
        self.project_repository = ProjectRepository(db)

    async def get_metrics_by_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> List[Metric]:
        experiment = await self.experiment_repository.get_experiment_if_accessible(
            user, experiment_id
        )
        if not experiment:
            return []

        query = select(Metric).where(Metric.experiment_id == experiment.id)
        result = await self.db.execute(query)
        return result.scalars().all()
