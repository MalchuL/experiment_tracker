from typing import List
from lib.db.base_repository import BaseRepository
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
