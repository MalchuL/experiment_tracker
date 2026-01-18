from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from domain.team.teams.repository import TeamRepository
from models import TeamRole


class Access(Enum):
    NONE = -1  # User is not a member of the team
    OWNER = 0
    MEMBER = 1
    VIEWER = 2
    ADMIN = 3


class Rights:
    def __init__(self, access: Access):
        self.access = access

    @property
    def can_view(self) -> bool:
        return self.access.value >= Access.VIEWER.value

    @property
    def can_edit(self) -> bool:
        return self.access.value >= Access.MEMBER.value

    @property
    def can_manage(self) -> bool:
        return self.access.value >= Access.OWNER.value

    @property
    def can_delete(self) -> bool:
        return self.access.value >= Access.OWNER.value

    @property
    def can_invite(self) -> bool:
        return self.access.value >= Access.OWNER.value


class AccessService:
    def __init__(self, db: AsyncSession):
        self.team_repository = TeamRepository(db)

    async def get_team_rights(self, user: UserProtocol, team_id: UUID_TYPE) -> Rights:
        team_member = await self.team_repository.get_team_member_if_accessible(
            user.id, team_id
        )
        if not team_member:
            return Rights(access=Access.NONE)
        return Rights(access=self._role_to_access(team_member.role))

    def _role_to_access(self, role: TeamRole) -> Access:
        match role:
            case TeamRole.OWNER:
                return Access.OWNER
            case TeamRole.ADMIN:
                return Access.ADMIN
            case TeamRole.MEMBER:
                return Access.MEMBER
            case TeamRole.VIEWER:
                return Access.VIEWER
            case _:
                return Access.NONE
