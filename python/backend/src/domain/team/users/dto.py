from fastapi_users import schemas
import uuid
from typing import Optional
from lib.datetime_types import ApiOptionalDateTime


class UserRead(schemas.BaseUser[uuid.UUID]):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: ApiOptionalDateTime = None


class UserCreate(schemas.BaseUserCreate):
    display_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
