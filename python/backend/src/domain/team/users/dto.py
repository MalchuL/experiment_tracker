import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import ConfigDict

from lib.datetime_types import ApiOptionalDateTime
from lib.dto_config import model_config as dto_model_config


def _user_read_config() -> ConfigDict:
    return ConfigDict(
        **{
            **dict(schemas.BaseUser[uuid.UUID].model_config),
            **dict(dto_model_config()),
        }
    )


def _user_create_config() -> ConfigDict:
    return ConfigDict(
        **{
            **dict(schemas.BaseUserCreate.model_config),
            **dict(dto_model_config()),
        }
    )


def _user_update_config() -> ConfigDict:
    return ConfigDict(
        **{
            **dict(schemas.BaseUserUpdate.model_config),
            **dict(dto_model_config()),
        }
    )


class UserRead(schemas.BaseUser[uuid.UUID]):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: ApiOptionalDateTime = None

    model_config = _user_read_config()


class UserCreate(schemas.BaseUserCreate):
    display_name: Optional[str] = None

    model_config = _user_create_config()


class UserUpdate(schemas.BaseUserUpdate):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = _user_update_config()
