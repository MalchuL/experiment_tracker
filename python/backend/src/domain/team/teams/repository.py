from typing import List
from uuid import UUID

from domain.team.teams.errors import TeamMemberNotFoundError
from lib.db.base_repository import BaseRepository
from lib.db.error import DBNotFoundError
from lib.types import UUID_TYPE
from models import Team, TeamMember, User
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class TeamRepository(BaseRepository[Team]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Team)
        self.team_member_repository = self._create_advanced_alchemy_repository(
            db, TeamMember
        )

    async def create(self, obj: Team) -> Team:
        return await self.advanced_alchemy_repository.add(obj, auto_refresh=True)

    async def update(self, id: str | UUID, **kwargs) -> Team:
        if "id" in kwargs:
            del kwargs["id"]
        existing_obj = await self.get_by_id(id)
        for key, value in kwargs.items():
            setattr(existing_obj, key, value)
        return await self.advanced_alchemy_repository.update(existing_obj)

    async def delete(self, id: str | UUID) -> None:
        return await self.advanced_alchemy_repository.delete(id)

    async def add_team_member(self, member: TeamMember) -> TeamMember:
        return await self.team_member_repository.add(member, auto_refresh=True)

    async def update_team_member(self, member: TeamMember) -> TeamMember:
        return await self.team_member_repository.update(member, auto_refresh=True)

    async def delete_team_member(
        self, user_id: UUID_TYPE, team_id: UUID_TYPE
    ) -> None:
        team_member = await self.team_member_repository.get_one_or_none(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id,
        )
        if team_member is None:
            raise TeamMemberNotFoundError("Team member not found")
        await self.team_member_repository.delete(team_member.id)

    async def get_accessible_teams(self, user: User) -> List[Team]:
        query = (
            select(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user.id)
        )
        result = await self.db.execute(query)
        teams = result.scalars().all()
        return list(teams)

    async def list_teams_for_user(self, user_id: UUID_TYPE) -> List[Team]:
        """Teams the user owns or is a member of (deduplicated)."""
        member_team_ids = select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        stmt = (
            select(Team)
            .where(or_(Team.owner_id == user_id, Team.id.in_(member_team_ids)))
            .order_by(Team.name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_team_members_with_users(self, team_id: UUID_TYPE) -> List[TeamMember]:
        stmt = (
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .options(selectinload(TeamMember.user))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_with_owner(self, team_id: UUID_TYPE) -> Team:
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.owner))
        )
        result = await self.db.execute(stmt)
        team = result.scalar_one_or_none()
        if team is None:
            raise DBNotFoundError(f"Team {team_id} not found")
        return team

    async def get_teams_by_ids(self, team_ids: List[UUID_TYPE]) -> List[Team]:
        if not team_ids:
            return []
        return await self.advanced_alchemy_repository.list(Team.id.in_(team_ids))

    async def get_team_member_if_accessible(
        self, user_id: UUID_TYPE, team_id: UUID_TYPE
    ) -> TeamMember | None:
        if team_id is None:
            raise ValueError("Team ID is required")
        return await self.team_member_repository.get_one_or_none(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id,
        )
