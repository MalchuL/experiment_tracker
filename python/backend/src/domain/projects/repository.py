from typing import List, Protocol
import uuid
from lib.db.base_repository import BaseRepository
from models import Project, User
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.team.teams.repository import TeamRepository


class UserProtocol(Protocol):
    id: uuid.UUID | str


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)
        self.team_repository = TeamRepository(db)

    async def get_user_team_ids(self, user: UserProtocol) -> List[uuid.UUID]:
        return await self.team_repository.get_accessible_teams(user)

    async def get_accessible_projects(self, user: UserProtocol) -> List[Project]:
        team_ids = await self.get_user_team_ids(user)

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
