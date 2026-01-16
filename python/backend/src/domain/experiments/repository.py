from typing import List
import uuid
from advanced_alchemy.filters import LimitOffset
from lib.db.base_repository import BaseRepository, ListOptions
from lib.types import UUID_TYPE
from models import Experiment, Project
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.repository import ProjectRepository, UserProtocol
from domain.team.teams.repository import TeamRepository


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Experiment)
        self.project_repository = ProjectRepository(db)
        self.team_repository = TeamRepository(db)

    async def _get_user_team_ids(self, user: UserProtocol) -> List[uuid.UUID]:
        teams = await self.team_repository.get_accessible_teams(user)
        return [team.id for team in teams]

    async def get_accessible_experiments(
        self, user: UserProtocol, list_options: ListOptions | None = None
    ) -> List[Experiment]:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))
        list_conditions = []
        if list_options:
            limit_offset = LimitOffset(
                offset=list_options.offset, limit=list_options.limit
            )
            list_conditions.append(limit_offset)

        result = await self.advanced_alchemy_repository.list(
            or_(*conditions),
            *list_conditions,
            order_by=Experiment.created_at.desc(),
        )
        return result

    async def get_experiments_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[Experiment]:
        project = await self.project_repository.get_project_if_accessible(
            user, project_id
        )
        if not project:
            return []

        experiments = await self.advanced_alchemy_repository.list(
            Experiment.project_id == project_id,
            order_by=(Experiment.order, False),  # descending (is_desc=False)
        )
        return experiments

    async def get_experiment_if_accessible(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment | None:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        return await self.advanced_alchemy_repository.get_one_or_none(
            Experiment.id == experiment_id,
            or_(*conditions),
        )
