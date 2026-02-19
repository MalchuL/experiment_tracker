from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class TeamRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamCreateRequest(BaseModel):
    name: str
    description: str | None = None


class TeamUpdateRequest(BaseModel):
    id: str
    name: str
    description: str | None = None


class TeamResponse(BaseModel):
    id: str
    createdAt: datetime
    ownerId: str
    name: str
    description: str | None = None


class TeamMemberCreateRequest(BaseModel):
    userId: str
    teamId: str
    role: TeamRole


class TeamMemberUpdateRequest(BaseModel):
    userId: str
    teamId: str
    role: TeamRole


class TeamMemberDeleteRequest(BaseModel):
    userId: str
    teamMemberId: str


class TeamMemberResponse(BaseModel):
    id: str
    userId: str
    teamId: str
    role: TeamRole


class SuccessResponse(BaseModel):
    success: bool
