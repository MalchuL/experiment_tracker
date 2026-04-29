"""User profile DTOs — JSON field names match Python attributes (camelCase)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Response shape for ``GET /users/me`` (wire JSON uses camelCase keys only)."""

    id: str
    email: str
    isActive: bool
    isSuperuser: bool
    isVerified: bool
    displayName: str | None = None
    avatarUrl: str | None = None
    createdAt: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class UserUpdateRequest(BaseModel):
    """Body for ``PATCH /users/me`` (optional fields; send only what changes)."""

    email: str | None = None
    password: str | None = None
    displayName: str | None = None
    avatarUrl: str | None = None
    isActive: bool | None = None
    isSuperuser: bool | None = None
    isVerified: bool | None = None

    model_config = ConfigDict(extra="forbid")
