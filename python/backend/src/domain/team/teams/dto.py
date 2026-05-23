import uuid
from typing import Optional

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)
from pydantic import BaseModel, Field

from lib.category_cleanup_dto import CategoryCleanupResponseDTO
from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from models import Role


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: Optional[str] = Field(
        default=None, max_length=ENTITY_DESCRIPTION_MAX_LEN
    )

    model_config = model_config()


class TeamReadDTO(TeamBase):
    id: uuid.UUID
    created_at: ApiDateTime
    owner_id: uuid.UUID | None = None


class TeamCreateDTO(TeamBase):
    pass


class TeamUpdateDTO(TeamBase):
    id: uuid.UUID


class TeamMemberBase(BaseModel):
    user_id: uuid.UUID
    team_id: uuid.UUID
    role: Role

    model_config = model_config()


class TeamMemberReadDTO(TeamMemberBase):
    id: uuid.UUID


class TeamMemberCreateDTO(TeamMemberBase):
    pass


class TeamMemberUpdateDTO(TeamMemberBase):
    pass


class TeamMemberDeleteDTO(BaseModel):
    """Remove a member from a team. ``team_id`` identifies the team (not the member row)."""

    user_id: uuid.UUID
    team_id: uuid.UUID

    model_config = model_config()


class TeamListItemDTO(TeamReadDTO):
    """Team row for list views with permission hints for the UI."""

    can_create_project: bool = False


class TeamUserLookupDTO(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    display_name: Optional[str] = None

    model_config = model_config()


class TeamMemberWithUserDTO(BaseModel):
    """Team member (or team owner) with profile fields for display."""

    member_id: uuid.UUID | None = None
    user_id: uuid.UUID
    team_id: uuid.UUID
    role: Role
    email: str | None = None
    display_name: str | None = None
    is_team_owner: bool = False

    model_config = model_config()


class TeamDeleteResponseDTO(CategoryCleanupResponseDTO):
    """Outcome of DELETE ``/teams/{id}`` (cleanup-shaped)."""

    model_config = model_config()
