from typing import List, Optional
from uuid import UUID

from experiment_tracker_shared.limits import (
    ENTITY_DESCRIPTION_MAX_LEN,
    ENTITY_NAME_MAX_LEN,
)
from pydantic import BaseModel, Field

from lib.datetime_types import ApiDateTime, ApiOptionalDateTime
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse


class ApiTokenCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=ENTITY_NAME_MAX_LEN)
    description: Optional[str] = Field(
        default=None, max_length=ENTITY_DESCRIPTION_MAX_LEN
    )
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: Optional[int] = Field(default=None, gt=0, le=3650)

    model_config = model_config()


class ApiTokenCreateResponseDTO(BaseModel):
    id: UUID
    name: str
    token: str
    created_at: ApiDateTime

    model_config = model_config()


class ApiTokenListItemDTO(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    created_at: ApiDateTime
    expires_at: ApiOptionalDateTime = None
    revoked: bool
    last_used_at: ApiOptionalDateTime = None

    model_config = model_config()


class ApiTokenListResponseDTO(PaginatedResponse[ApiTokenListItemDTO]):
    model_config = model_config()


class ApiTokenUpdateDTO(BaseModel):
    name: Optional[str] = Field(
        default=None, min_length=1, max_length=ENTITY_NAME_MAX_LEN
    )
    description: Optional[str] = Field(
        default=None, max_length=ENTITY_DESCRIPTION_MAX_LEN
    )
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = Field(default=None, gt=0, le=3650)

    model_config = model_config()
