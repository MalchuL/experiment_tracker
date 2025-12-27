import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi_users import schemas
from datetime import datetime

from .models import TeamRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    display_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamMemberRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: Optional[str] = None
    role: TeamRole
    joined_at: datetime

    class Config:
        from_attributes = True


class TeamRead(TeamBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    members: List[TeamMemberRead] = []

    class Config:
        from_attributes = True


class TeamMemberAdd(BaseModel):
    email: str
    role: TeamRole = TeamRole.MEMBER


class TeamMemberUpdateRole(BaseModel):
    role: TeamRole
