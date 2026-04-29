"""Admin HTTP API gated by ``X-Admin-Key`` (see ``Settings.admin_panel_key`` / ``ADMIN_PANEL_KEY``).

These routes are **not** tied to JWT or ``User.is_superuser``. Anyone who presents the
configured shared header can list all users/teams (paginated) and reset passwords. Use a
strong ``ADMIN_PANEL_KEY`` and restrict exposure in production.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated, Optional

from api.routes.auth import get_user_manager
from config.settings import get_settings
from db.database import get_async_session
from domain.team.users.dto import UserUpdate
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi_users import BaseUserManager, exceptions
from pydantic import BaseModel
from sqlalchemy import func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.dto_config import model_config as dto_model_config
from models import Team, User

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_ADMIN_LIST = 100


async def require_admin_panel_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    """Reject the request unless ``X-Admin-Key`` matches ``Settings.admin_panel_key`` (constant-time)."""
    settings = get_settings()
    expected = settings.admin_panel_key
    if x_admin_key is None:
        raise HTTPException(status_code=403, detail="Missing X-Admin-Key header")
    if len(x_admin_key) != len(expected):
        # timing: still run compare_digest on equal-length dummy
        secrets.compare_digest(expected.encode("utf-8"), expected.encode("utf-8"))
        raise HTTPException(status_code=403, detail="Invalid admin key")
    if not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=403, detail="Invalid admin key")


class AdminUserRowDTO(BaseModel):
    """Safe JSON row for a user in the admin panel list (no secrets or ORM extras)."""

    model_config = dto_model_config()

    id: uuid.UUID
    email: str
    display_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: Optional[str] = None


class AdminTeamRowDTO(BaseModel):
    """Safe JSON row for a team in the admin panel list."""

    model_config = dto_model_config()

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    owner_id: uuid.UUID
    created_at: Optional[str] = None


class AdminResetPasswordResponse(BaseModel):
    """One-time response after forcing a new password (plaintext shown only in this payload)."""

    model_config = dto_model_config()

    user_id: uuid.UUID
    email: str
    temporary_password: str


@router.get(
    "/users",
    response_model=list[AdminUserRowDTO],
    response_model_by_alias=True,
)
async def admin_panel_list_all_users(
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=MAX_ADMIN_LIST),
    offset: int = Query(default=0, ge=0),
) -> list[AdminUserRowDTO]:
    """Return a global, paginated catalog of user accounts (optional ``q`` filters email and display name)."""
    stmt = select(User).order_by(User.email).offset(offset).limit(limit)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = (
            select(User)
            .where(
                or_(
                    func.lower(User.email).like(needle),
                    func.lower(func.coalesce(User.display_name, literal(""))).like(needle),
                )
            )
            .order_by(User.email)
            .offset(offset)
            .limit(limit)
        )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    out: list[AdminUserRowDTO] = []
    for u in rows:
        out.append(
            AdminUserRowDTO(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                created_at=u.created_at.isoformat() if u.created_at else None,
            )
        )
    return out


@router.get(
    "/teams",
    response_model=list[AdminTeamRowDTO],
    response_model_by_alias=True,
)
async def admin_panel_list_all_teams(
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=MAX_ADMIN_LIST),
    offset: int = Query(default=0, ge=0),
) -> list[AdminTeamRowDTO]:
    """Return a global, paginated catalog of teams (optional ``q`` filters name and description)."""
    stmt = select(Team).order_by(Team.name).offset(offset).limit(limit)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = (
            select(Team)
            .where(
                or_(
                    func.lower(Team.name).like(needle),
                    func.lower(func.coalesce(Team.description, literal(""))).like(needle),
                )
            )
            .order_by(Team.name)
            .offset(offset)
            .limit(limit)
        )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        AdminTeamRowDTO(
            id=t.id,
            name=t.name,
            description=t.description,
            owner_id=t.owner_id,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in rows
    ]


@router.post(
    "/users/{user_id}/reset-password",
    response_model=AdminResetPasswordResponse,
    response_model_by_alias=True,
)
async def admin_panel_reset_user_password(
    user_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
    user_manager: BaseUserManager[User, uuid.UUID] = Depends(get_user_manager),
) -> AdminResetPasswordResponse:
    """Set the user's password to a new random value; the plaintext is returned only in this response."""
    try:
        user = await user_manager.get(user_id)
    except exceptions.UserNotExists as e:
        raise HTTPException(status_code=404, detail="User not found") from e

    temporary_password = secrets.token_urlsafe(16)
    try:
        await user_manager.update(
            UserUpdate(password=temporary_password),
            user,
            safe=True,
            request=None,
        )
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=400,
            detail={"reason": e.reason},
        ) from e

    await db.commit()
    return AdminResetPasswordResponse(
        user_id=user.id,
        email=user.email,
        temporary_password=temporary_password,
    )
