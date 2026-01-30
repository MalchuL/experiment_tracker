from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from lib.dto_config import model_config


class ApiTokenCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: Optional[int] = Field(default=None, gt=0, le=3650)

    model_config = model_config()


class ApiTokenCreateResponseDTO(BaseModel):
    id: UUID
    name: str
    token: str
    created_at: datetime

    model_config = model_config()


class ApiTokenListItemDTO(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked: bool
    last_used_at: Optional[datetime] = None

    model_config = model_config()


class ApiTokenUpdateDTO(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = Field(default=None, gt=0, le=3650)

    model_config = model_config()
