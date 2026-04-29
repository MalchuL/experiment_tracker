import uuid
from typing import List, Optional

from pydantic import BaseModel

from lib.datetime_types import ApiDateTime
from lib.dto_config import model_config
from models import Role


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamReadDTO(TeamBase):
    id: uuid.UUID
    created_at: ApiDateTime
    owner_id: uuid.UUID
    model_config = model_config()


class TeamCreateDTO(TeamBase):
    model_config = model_config()


class TeamUpdateDTO(TeamBase):
    id: uuid.UUID
    model_config = model_config()


class TeamMemberBase(BaseModel):
    user_id: uuid.UUID
    team_id: uuid.UUID
    role: Role


class TeamMemberReadDTO(TeamMemberBase):
    id: uuid.UUID
    model_config = model_config()


class TeamMemberCreateDTO(TeamMemberBase):
    model_config = model_config()


class TeamMemberUpdateDTO(TeamMemberBase):
    model_config = model_config()


class TeamMemberDeleteDTO(BaseModel):
    """Remove a member from a team. ``team_id`` identifies the team (not the member row)."""

    user_id: uuid.UUID
    team_id: uuid.UUID
    model_config = model_config()


class TeamListItemDTO(TeamReadDTO):
    """Team row for list views with permission hints for the UI."""

    can_create_project: bool = False
    model_config = model_config()


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
