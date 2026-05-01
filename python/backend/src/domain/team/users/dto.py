"""User DTOs for FastAPI Users–backed routes.

These models subclass ``fastapi_users.schemas`` bases (email, password, flags, …).
We merge each base's ``model_config`` with :func:`lib.dto_config.model_config` via
:func:`_merge_model_config` so we keep whatever defaults fastapi-users relies on **and**
apply this app's JSON conventions (camelCase aliases, ``extra="forbid"``, etc.). Replacing
the config with only one side would either drift from other endpoints on the wire or risk
dropping behavior expected by the library bases.

**Typing:** Pydantic's ``ConfigDict`` is modeled as a structured mapping for static analysis.
Building it by splatting ``dict[str, object]`` into ``ConfigDict(...)`` triggers mypy's
``typeddict-item`` error. We merge plain dicts, then :func:`typing.cast` the result back to
``ConfigDict`` (same runtime object).
"""

import uuid
from typing import Any, Optional, cast

from fastapi_users import schemas
from pydantic import ConfigDict

from lib.datetime_types import ApiOptionalDateTime
from lib.dto_config import model_config as dto_model_config


def _merge_model_config(base: ConfigDict) -> ConfigDict:
    """Merge fastapi-users ``model_config`` with app-wide DTO settings.

    Runtime: shallow merge; later keys from ``dto_model_config()`` win on collisions
    (camelCase aliases, ``extra``, …). Static typing: see module docstring.
    """

    merged: dict[str, Any] = {**dict(base), **dict(dto_model_config())}
    return cast(ConfigDict, merged)


def _user_read_config() -> ConfigDict:
    """Merge ``BaseUser`` config with app-wide DTO settings (camelCase JSON, …)."""

    return _merge_model_config(schemas.BaseUser[uuid.UUID].model_config)


def _user_create_config() -> ConfigDict:
    """Merge ``BaseUserCreate`` config with app-wide DTO settings."""

    return _merge_model_config(schemas.BaseUserCreate.model_config)


def _user_update_config() -> ConfigDict:
    """Merge ``BaseUserUpdate`` config with app-wide DTO settings."""

    return _merge_model_config(schemas.BaseUserUpdate.model_config)


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Public user shape returned by auth/profile routes."""

    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: ApiOptionalDateTime = None

    model_config = _user_read_config()


class UserCreate(schemas.BaseUserCreate):
    """Payload for registration / user creation (extends base email + password)."""

    display_name: Optional[str] = None

    model_config = _user_create_config()


class UserUpdate(schemas.BaseUserUpdate):
    """Patch payload for user profile updates."""

    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = _user_update_config()
