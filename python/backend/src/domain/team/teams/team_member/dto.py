from uuid import UUID
from pydantic import BaseModel

from .roles import TeamRole
from .rights import Rights


model_config = ConfigDict(
    alias_generator=AliasGenerator(
        validation_alias=to_camel,  # Input: FirstName -> first_name
        serialization_alias=to_camel,  # Output: first_name -> firstName
    ),
    extra="forbid",
    populate_by_name=True,
)


class TeamMemberBaseDTO(BaseModel):
    user_id: UUID
    team_id: UUID
    role: TeamRole | None = None
    rights: Rights | None = None

    model_config = model_config
