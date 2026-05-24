from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from ...pagination import PaginatedResponse


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
    ownerId: str | None = None
    name: str
    description: str | None = None


class TeamListItemResponse(TeamResponse):
    canCreateProject: bool = False


class TeamListResponse(PaginatedResponse[TeamListItemResponse]):
    pass


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
    teamId: str


class TeamMemberResponse(BaseModel):
    id: str
    userId: str
    teamId: str
    role: TeamRole


class SuccessResponse(BaseModel):
    success: bool
