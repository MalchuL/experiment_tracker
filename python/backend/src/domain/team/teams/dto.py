import uuid
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from models import TeamRole
from lib.dto_config import model_config


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamReadDTO(TeamBase):
    id: uuid.UUID
    created_at: datetime
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
    role: TeamRole


class TeamMemberReadDTO(TeamMemberBase):
    id: uuid.UUID
    model_config = model_config()


class TeamMemberCreateDTO(TeamMemberBase):
    model_config = model_config()


class TeamMemberUpdateDTO(TeamMemberBase):
    model_config = model_config()


class TeamMemberDeleteDTO(BaseModel):
    user_id: uuid.UUID
    team_member_id: uuid.UUID
    model_config = model_config()
