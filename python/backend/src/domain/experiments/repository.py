from typing import List
import uuid
from lib.db.base_repository import BaseRepository
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

    async def get_accessible_experiments(self, user: UserProtocol) -> List[Experiment]:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Experiment)
            .join(Project)
            .where(or_(*conditions))
            .order_by(Experiment.created_at.desc())
        )

        result = await self.db.execute(query)
        experiments = result.scalars().all()
        return list(experiments)

    async def get_experiments_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[Experiment]:
        project = await self.project_repository.get_project_if_accessible(
            user, project_id
        )
        if not project:
            return []

        query = (
            select(Experiment)
            .where(Experiment.project_id == project_id)
            .order_by(Experiment.order)
        )

        result = await self.db.execute(query)
        experiments = result.scalars().all()
        return list(experiments)

    async def get_experiment_if_accessible(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> Experiment | None:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Experiment)
            .join(Project)
            .where(Experiment.id == experiment_id, or_(*conditions))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
