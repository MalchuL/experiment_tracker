from typing import List, Literal, Sequence
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import Experiment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.protocols.user_protocol import UserProtocol
from sqlalchemy.orm import selectinload


LoadOptions = Sequence[Literal["project", "metrics"]] | bool


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Experiment)

    async def get_user_experiments(
        self, user: UserProtocol, list_options: ListOptions | None = None
    ) -> Page[Experiment]:
        return await self.list(
            Experiment.started_by == user.id,
            order_by=Experiment.created_at.desc(),
            list_options=list_options,
        )

    async def get_latest_experiments(
        self,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(limit=10, offset=0),
    ) -> Page[Experiment]:
        return await self.list(
            Experiment.project_id == project_id,
            order_by=Experiment.created_at.desc(),
            list_options=list_options,
        )

    async def get_experiments_by_project(
        self,
        project_id: UUID_TYPE,
        full_load: LoadOptions = False,
        list_options: ListOptions | None = None,
    ) -> Page[Experiment]:
        if isinstance(full_load, Sequence):
            load = [selectinload(getattr(Experiment, option)) for option in full_load]
        elif full_load:
            load = [selectinload(Experiment.project), selectinload(Experiment.metrics)]
        else:
            load = []
        return await self.list(
            Experiment.project_id == project_id,
            order_by=[Experiment.created_at.desc(), Experiment.id.desc()],
            load=load,
            list_options=list_options,
        )

    async def get_experiments_by_ids(
        self, experiment_ids: List[UUID_TYPE]
    ) -> List[Experiment]:
        if not experiment_ids:
            return []
        experiments = list(
            await self.advanced_alchemy_repository.list(
                Experiment.id.in_(experiment_ids),
            )
        )
        return experiments

    async def list_experiment_ids_for_project_by_created_at_desc(
        self, project_id: UUID_TYPE
    ) -> List[UUID_TYPE]:
        """Project experiment ids for paging UIs: newest first, stable on id."""
        stmt = (
            select(Experiment.id)
            .where(Experiment.project_id == project_id)
            .order_by(Experiment.created_at.desc(), Experiment.id.desc())
        )
        res = await self.db.execute(stmt)
        return [r[0] for r in res.all()]
