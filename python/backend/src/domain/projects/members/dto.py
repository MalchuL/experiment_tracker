import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field

from lib.dto_config import model_config
from models import Role


class ProjectMemberRowDTO(BaseModel):
    user_id: uuid.UUID
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Role
    access_source: Literal["direct", "team", "override"]
    can_edit: bool = False
    can_remove: bool = False
    model_config = model_config()


class ProjectMemberInviteDTO(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: Role = Field(default=Role.MEMBER)
    model_config = model_config()


class ProjectMemberUpdateRoleDTO(BaseModel):
    user_id: uuid.UUID
    role: Role
    model_config = model_config()


class ProjectMemberRemoveDTO(BaseModel):
    user_id: uuid.UUID
    model_config = model_config()


class UserLookupDTO(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    display_name: Optional[str] = None
    model_config = model_config()
