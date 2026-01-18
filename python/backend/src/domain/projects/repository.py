from typing import List, Optional, Protocol
import uuid
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Project, User
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from advanced_alchemy.repository.typing import OrderingPair
from domain.team.teams.repository import TeamRepository
from lib.protocols.user_protocol import UserProtocol


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)
        self.team_repository = TeamRepository(db)

    async def _get_user_team_ids(self, user: UserProtocol) -> List[uuid.UUID]:
        teams = await self.team_repository.get_accessible_teams(user)
        return [team.id for team in teams]

    async def get_accessible_projects(
        self,
        user: UserProtocol,
        sort_by: OrderingPair | None = None,
        full_load: bool = True,
    ) -> List[Project]:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))

        if full_load:
            options = [
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            ]
        else:
            options = []

        result = await self.advanced_alchemy_repository.list(
            or_(*conditions), load=options, order_by=sort_by
        )
        return result

    async def get_project_if_accessible(
        self, user: UserProtocol, project_id: UUID_TYPE, full_load: bool = True
    ) -> Project | None:
        team_ids = await self._get_user_team_ids(user)

        conditions = [Project.owner_id == user.id]
        if team_ids:
            conditions.append(Project.team_id.in_(team_ids))
        if full_load:
            options = [
                selectinload(Project.owner),
                selectinload(Project.experiments),
                selectinload(Project.hypotheses),
                selectinload(Project.team),
            ]
        else:
            options = []

        result = await self.advanced_alchemy_repository.get_one_or_none(
            Project.id == project_id, or_(*conditions), load=options
        )
        return result

    async def get_projects_by_team(self, team_id: UUID_TYPE) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.team_id == team_id)

    async def get_projects_by_ids(self, project_ids: List[UUID_TYPE]) -> List[Project]:
        return await self.advanced_alchemy_repository.list(Project.id.in_(project_ids))
