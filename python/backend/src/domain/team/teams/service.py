from sqlalchemy.ext.asyncio import AsyncSession
from domain.team.teams.repository import TeamRepository
from domain.rbac.service import PermissionService
from domain.rbac.permissions import TeamActions
from uuid import UUID
from domain.team.teams.errors import (
    TeamMemberAlreadyExistsError,
    TeamAccessDeniedError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from lib.db.error import DBNotFoundError
from .dto import (
    TeamCreateDTO,
    TeamMemberUpdateDTO,
    TeamReadDTO,
    TeamMemberCreateDTO,
    TeamMemberDeleteDTO,
    TeamMemberReadDTO,
    TeamUpdateDTO,
)
from .mapper import TeamMapper, CreateDTOToSchemaProps
from models import TeamRole


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.team_repository = TeamRepository(db)
        self.permission_service = PermissionService(db, auto_commit=False)
        self.team_mapper = TeamMapper()

    # Team
    async def create_team(self, user_id: UUID, dto: TeamCreateDTO) -> TeamReadDTO:
        team = self.team_mapper.team_dto_to_schema(
            dto, CreateDTOToSchemaProps(owner_id=user_id)
        )
        await self.team_repository.create(team)
        await self.permission_service.add_user_to_team_permissions(
            user_id, team.id, TeamRole.OWNER
        )
        await self.permission_service.commit()
        return self.team_mapper.team_schema_to_dto(team)

    async def update_team(self, user_id: UUID, dto: TeamUpdateDTO) -> TeamReadDTO:
        if not await self.permission_service.has_permission(
            user_id=user_id, team_id=dto.id, action=TeamActions.MANAGE_TEAM
        ):
            raise TeamAccessDeniedError("You do not have permission to update a team")
        try:
            await self.team_repository.get_by_id(dto.id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        update_data = self.team_mapper.team_update_dto_to_dict(dto)
        update_data.pop("id", None)
        team = await self.team_repository.update(dto.id, **update_data)
        await self.permission_service.commit()
        return self.team_mapper.team_schema_to_dto(team)

    async def delete_team(self, user_id: UUID, team_id: UUID) -> None:
        if not await self.permission_service.has_permission(
            user_id=user_id, team_id=team_id, action=TeamActions.MANAGE_TEAM
        ):
            raise TeamAccessDeniedError("You do not have permission to delete a team")
        try:
            await self.team_repository.get_by_id(team_id)
        except DBNotFoundError:
            raise TeamNotFoundError("Team not found")
        await self.team_repository.delete(team_id)
        await self.db.commit()

    # Team Member
    async def add_team_member(
        self, user_id: UUID, team_member: TeamMemberCreateDTO
    ) -> TeamMemberReadDTO:
        if not await self.permission_service.has_permission(
            user_id, TeamActions.MANAGE_TEAM, team_member.team_id
        ):
            raise TeamAccessDeniedError(
                "You do not have permission to add a team member"
            )
        if await self.team_repository.get_team_member_if_accessible(
            team_member.user_id, team_member.team_id
        ):
            raise TeamMemberAlreadyExistsError("Team member already exists")

        team_member = self.team_mapper.team_member_dto_to_schema(team_member)
        await self.team_repository.add_team_member(team_member)
        await self.permission_service.add_user_to_team_permissions(
            team_member.user_id, team_member.team_id, team_member.role
        )
        await self.permission_service.commit()
        return self.team_mapper.team_member_schema_to_dto(team_member)

    async def update_team_member(self, user_id: UUID, dto: TeamMemberUpdateDTO) -> None:
        if not await self.permission_service.has_permission(
            user_id, TeamActions.MANAGE_TEAM, dto.team_id
        ):
            raise TeamAccessDeniedError(
                "You do not have permission to add a team member"
            )
        team_member = await self.team_repository.get_team_member_if_accessible(
            dto.user_id, dto.team_id
        )

        # TODO Add validation for role change e.g. owner cannot be removed, owner cannot be demoted to member, etc.

        if team_member is None:
            raise TeamMemberNotFoundError("Team member not found")
        team_member.role = dto.role
        await self.team_repository.update_team_member(team_member)
        await self.permission_service.update_user_team_role_permissions(
            dto.user_id, dto.team_id, dto.role
        )
        await self.permission_service.commit()
        return self.team_mapper.team_member_schema_to_dto(team_member)

    async def remove_team_member(self, user_id: UUID, dto: TeamMemberDeleteDTO) -> None:

        if str(user_id) != str(
            dto.user_id
        ) and not await self.permission_service.has_permission(
            user_id, TeamActions.MANAGE_TEAM, dto.team_member_id
        ):
            raise TeamAccessDeniedError(
                "You do not have permission to remove a team member"
            )
        await self.team_repository.delete_team_member(dto.user_id, dto.team_member_id)
        await self.permission_service.remove_user_from_team_permissions(
            dto.user_id, dto.team_member_id
        )
        await self.permission_service.commit()
