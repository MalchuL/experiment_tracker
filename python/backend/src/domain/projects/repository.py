from typing import List, Optional, Protocol
import uuid
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Project, User
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.team.teams.repository import TeamRepository
from lib.protocols.user_protocol import UserProtocol


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)
        self.team_repository = TeamRepository(db)

    async def _get_user_team_ids(self, user: UserProtocol) -> List[uuid.UUID]:
        teams = await self.team_repository.get_accessible_teams(user)
        return [team.id for team in teams]

    async def get_accessible_projects(self, user: UserProtocol) -> List[Project]:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Project)
            .options(
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            )
            .where(or_(*conditions))
            .order_by(Project.created_at.desc())
        )

        result = await self.db.execute(query)
        projects = result.scalars().all()
        return list(projects)

    async def get_project_if_accessible(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> Project | None:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        query = (
            select(Project)
            .options(
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            )
            .where(Project.id == project_id, or_(*conditions))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
