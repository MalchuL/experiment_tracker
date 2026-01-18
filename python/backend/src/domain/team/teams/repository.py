from typing import List
import uuid
from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import Team, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import TeamMember


class TeamRepository(BaseRepository[Team]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Team)

    async def get_accessible_teams(self, user: User) -> List[Team]:
        query = (
            select(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user.id)
        )
        result = await self.db.execute(query)
        teams = result.scalars().all()
        return list(teams)

    async def get_teams_by_ids(self, team_ids: List[UUID_TYPE]) -> List[Team]:
        if not team_ids:
            return []
        return await self.advanced_alchemy_repository.list(Team.id.in_(team_ids))

    async def get_team_member_if_accessible(
        self, user_id: UUID_TYPE, team_id: UUID_TYPE
    ) -> TeamMember | None:
        if team_id is None:
            raise ValueError("Team ID is required")
        query = (
            select(TeamMember)
            .where(TeamMember.user_id == user_id, TeamMember.team_id == team_id)
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
