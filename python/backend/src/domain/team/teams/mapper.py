from typing import Any, Dict
from dataclasses import dataclass
import uuid
from domain.team.teams.dto import (
    TeamCreateDTO,
    TeamUpdateDTO,
    TeamMemberCreateDTO,
    TeamMemberUpdateDTO,
    TeamReadDTO,
    TeamMemberReadDTO,
)
from models import Team, TeamMember
from lib.dto_converter import DtoConverter


@dataclass
class CreateDTOToSchemaProps:
    owner_id: uuid.UUID


class TeamMapper:
    # Team
    def team_dto_to_schema(
        self, dto: TeamCreateDTO, props: CreateDTOToSchemaProps
    ) -> Team:
        return Team(
            name=dto.name,
            description=dto.description,
            owner_id=props.owner_id,
        )

    def team_schema_to_dto(self, team: Team) -> TeamReadDTO:
        return TeamReadDTO(
            id=team.id,
            name=team.name,
            description=team.description,
            owner_id=team.owner_id,
            created_at=team.created_at,
        )

    def team_update_dto_to_dict(self, dto: TeamUpdateDTO) -> Dict[str, Any]:
        converter = DtoConverter[TeamUpdateDTO](TeamUpdateDTO)
        return converter.dto_to_partial_dict_with_dto_case(dto)

    # Team Member
    def team_member_dto_to_schema(self, dto: TeamMemberCreateDTO) -> TeamMember:
        return TeamMember(
            user_id=dto.user_id,
            team_id=dto.team_id,
            role=dto.role,
        )

    def team_member_schema_to_dto(self, team_member: TeamMember) -> TeamMemberReadDTO:
        return TeamMemberReadDTO(
            id=team_member.id,
            user_id=team_member.user_id,
            team_id=team_member.team_id,
            role=team_member.role,
        )
