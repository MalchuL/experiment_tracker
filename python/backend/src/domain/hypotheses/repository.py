from typing import List
import uuid
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Hypothesis, Project
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.projects.repository import ProjectRepository
from domain.team.teams.repository import TeamRepository
from lib.protocols.user_protocol import UserProtocol


class HypothesisRepository(BaseRepository[Hypothesis]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Hypothesis)
        self.project_repository = ProjectRepository(db)
        self.team_repository = TeamRepository(db)

    async def _get_user_team_ids(self, user: UserProtocol) -> List[uuid.UUID]:
        teams = await self.team_repository.get_accessible_teams(user)
        return [team.id for team in teams]

    async def get_accessible_hypotheses(self, user: UserProtocol) -> List[Hypothesis]:
        team_ids = await self._get_user_team_ids(user)
        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Hypothesis)
            .join(Project)
            .where(or_(*conditions))
            .order_by(Hypothesis.created_at.desc())
        )

        result = await self.db.execute(query)
        hypotheses = result.scalars().all()
        return list(hypotheses)

    async def get_hypotheses_by_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> List[Hypothesis]:
        project = await self.project_repository.get_project_if_accessible(
            user, project_id
        )
        if not project:
            return []

        query = (
            select(Hypothesis)
            .where(Hypothesis.project_id == project_id)
            .order_by(Hypothesis.created_at.desc())
        )

        result = await self.db.execute(query)
        hypotheses = result.scalars().all()
        return list(hypotheses)

    async def get_hypothesis_if_accessible(
        self, user: UserProtocol, hypothesis_id: UUID_TYPE
    ) -> Hypothesis | None:
        team_ids = await self._get_user_team_ids(user)
        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Hypothesis)
            .join(Project)
            .where(Hypothesis.id == hypothesis_id, or_(*conditions))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
