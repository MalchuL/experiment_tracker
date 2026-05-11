"""Admin HTTP API gated by ``X-Admin-Key`` (see ``Settings.admin_panel_key`` / ``ADMIN_PANEL_KEY``).

These routes are **not** tied to JWT or ``User.is_superuser``. Anyone who presents the
configured shared header can list all users/teams (paginated) and reset passwords. Use a
strong ``ADMIN_PANEL_KEY`` and restrict exposure in production.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated, Optional

from api.routes.admin_dto import AdminUserDeleteResponseDTO
from api.routes.auth import get_user_manager
from config.settings import get_settings
from db.database import get_async_session
from domain.team.users.dto import UserUpdate
from clients.object_storage import ObjectStorageClient
from clients.object_storage.dto import (
    StorageBucketClearResponseDTO,
    StorageBucketDeleteResponseDTO,
    StorageBucketListResponseDTO,
    StorageBucketReconcileResponseDTO,
)
from clients.scalars import ScalarsServiceClient
from clients.scalars.dto import (
    ScalarsDropStorageTableResponseDTO,
    ScalarsListStorageTablesResponseDTO,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi_users import BaseUserManager, exceptions
from pydantic import BaseModel
from sqlalchemy import String, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.category_cleanup_dto import (
    CategoryCleanupErrorEntryDTO,
    CategoryCleanupResultEntryDTO,
)
from lib.deletion_outcome import (
    append_postgres_deleted,
    finalize_deletion_outcome,
    outcome_lists_from_project_teardown,
)
from lib.dto_config import model_config as dto_model_config
from domain.scalars.service import NoOpScalarsService
from domain.projects.satellite_teardown import teardown_project_for_delete
from models import Experiment, Project, Team, User

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
    owner_id: uuid.UUID | None = None
    created_at: Optional[str] = None


class AdminUserListResponse(BaseModel):
    """Paginated user catalog for the admin panel."""

    model_config = dto_model_config()

    items: list[AdminUserRowDTO]
    total: int
    limit: int
    offset: int


class AdminTeamListResponse(BaseModel):
    """Paginated team catalog for the admin panel."""

    model_config = dto_model_config()

    items: list[AdminTeamRowDTO]
    total: int
    limit: int
    offset: int


class AdminResetPasswordResponse(BaseModel):
    """One-time response after forcing a new password (plaintext shown only in this payload)."""

    model_config = dto_model_config()

    user_id: uuid.UUID
    email: str
    temporary_password: str


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    response_model_by_alias=True,
)
async def admin_panel_list_all_users(
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=MAX_ADMIN_LIST),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListResponse:
    """Return a global, paginated catalog of user accounts.

    Optional ``q`` filters email, display name, and user id (substring match on UUID text).
    """
    if q and q.strip():
        qq = q.strip()
        needle = f"%{qq.lower()}%"
        id_as_text = cast(User.id, String)
        filter_expr = or_(
            func.lower(User.email).like(needle),
            func.lower(func.coalesce(User.display_name, literal(""))).like(needle),
            id_as_text.ilike(f"%{qq}%"),
        )
        stmt = select(User).where(filter_expr).order_by(User.email)
        count_stmt = select(func.count()).select_from(User).where(filter_expr)
    else:
        stmt = select(User).order_by(User.email)
        count_stmt = select(func.count()).select_from(User)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    result = await db.execute(stmt.offset(offset).limit(limit))
    rows = result.scalars().all()
    items = [
        AdminUserRowDTO(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in rows
    ]
    return AdminUserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/teams",
    response_model=AdminTeamListResponse,
    response_model_by_alias=True,
)
async def admin_panel_list_all_teams(
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=MAX_ADMIN_LIST),
    offset: int = Query(default=0, ge=0),
) -> AdminTeamListResponse:
    """Return a global, paginated catalog of teams (optional ``q`` filters name and description)."""
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        filter_expr = or_(
            func.lower(Team.name).like(needle),
            func.lower(func.coalesce(Team.description, literal(""))).like(needle),
        )
        stmt = select(Team).where(filter_expr).order_by(Team.name)
        count_stmt = select(func.count()).select_from(Team).where(filter_expr)
    else:
        stmt = select(Team).order_by(Team.name)
        count_stmt = select(func.count()).select_from(Team)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    result = await db.execute(stmt.offset(offset).limit(limit))
    rows = result.scalars().all()
    items = [
        AdminTeamRowDTO(
            id=t.id,
            name=t.name,
            description=t.description,
            owner_id=t.owner_id,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in rows
    ]
    return AdminTeamListResponse(items=items, total=total, limit=limit, offset=offset)


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


@router.post("/users/{user_id}/deactivate", response_model=AdminUserRowDTO)
async def admin_panel_deactivate_user(
    user_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
) -> AdminUserRowDTO:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return AdminUserRowDTO(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/users/{user_id}/reactivate", response_model=AdminUserRowDTO)
async def admin_panel_reactivate_user(
    user_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
) -> AdminUserRowDTO:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return AdminUserRowDTO(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.delete("/users/{user_id}", response_model=AdminUserDeleteResponseDTO)
async def admin_panel_delete_user(
    user_id: uuid.UUID,
    detailed: bool = Query(
        False,
        description=(
            "When true, include full per-step ``results``. "
            "When false (default), ``results`` is empty and ``resultCount`` counts successes."
        ),
    ),
    _: None = Depends(require_admin_panel_key),
    db: AsyncSession = Depends(get_async_session),
) -> AdminUserDeleteResponseDTO:
    """Remove personal (non-team) projects for this user, then the user row.

    Team-scoped projects are intentionally not bulk-deleted; ``owner_id`` becomes null
    via FK when the user is removed.

    For each **personal** project, runs the same satellite teardown as interactive project
    deletion before removing the project ORM row. Per-step outcomes are captured in the
    response for operator visibility.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="User must be inactive before deletion")
    settings = get_settings()
    object_client = (
        ObjectStorageClient(settings.object_storage_service_url)
        if settings.object_storage_service_url
        else None
    )
    scalars_svc = (
        ScalarsServiceClient(settings.scalars_service_url)
        if settings.scalars_service_url
        else NoOpScalarsService()
    )
    result = await db.execute(
        select(Project).where(Project.owner_id == user_id, Project.team_id.is_(None))
    )
    personal_projects = list(result.scalars().all())
    results: list[CategoryCleanupResultEntryDTO] = []
    errors: list[CategoryCleanupErrorEntryDTO] = []
    for project in personal_projects:
        experiments_result = await db.execute(
            select(Experiment).where(Experiment.project_id == project.id)
        )
        experiment_ids = [e.id for e in experiments_result.scalars().all()]
        teardown = await teardown_project_for_delete(
            project.id,
            experiment_ids,
            object_client,
            scalars_svc,
        )
        r, e = outcome_lists_from_project_teardown(teardown)
        results.extend(r)
        errors.extend(e)
        await db.delete(project)
        append_postgres_deleted(
            results, category="postgres:project", entity_id=project.id
        )
    await db.delete(user)
    await db.commit()
    append_postgres_deleted(results, category="postgres:user", entity_id=user_id)
    finalized = finalize_deletion_outcome(results, errors, detailed=detailed)
    return AdminUserDeleteResponseDTO.model_validate(finalized.model_dump())


@router.get("/storage/buckets", response_model=StorageBucketListResponseDTO)
async def admin_panel_list_storage_buckets(
    _: None = Depends(require_admin_panel_key),
    project_id: uuid.UUID | None = Query(default=None),
    experiment_id: uuid.UUID | None = Query(default=None),
    reconcile: bool = Query(
        default=False,
        description=(
            "When true, each row includes storageSize (sum of object sizes from object storage). "
            "Does not update the registry size; use POST .../storage/buckets/{bucket_id}/reconcile to persist."
        ),
    ),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> StorageBucketListResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketListResponseDTO(
            buckets=[],
            total=0,
            limit=limit,
            offset=offset,
        )
    return await ObjectStorageClient(settings.object_storage_service_url).list_buckets(
        project_id=project_id,
        experiment_id=experiment_id,
        reconcile=reconcile,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/storage/buckets/storage-only",
    response_model=StorageBucketDeleteResponseDTO,
)
async def admin_panel_delete_storage_only_bucket(
    _: None = Depends(require_admin_panel_key),
    name: str = Query(..., min_length=1, max_length=255),
) -> StorageBucketDeleteResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketDeleteResponseDTO(deleted=False)
    return await ObjectStorageClient(
        settings.object_storage_service_url
    ).delete_storage_only_bucket(name)


@router.post(
    "/storage/buckets/storage-only/clear",
    response_model=StorageBucketClearResponseDTO,
)
async def admin_panel_clear_storage_only_bucket(
    _: None = Depends(require_admin_panel_key),
    name: str = Query(..., min_length=1, max_length=255),
) -> StorageBucketClearResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketClearResponseDTO(cleared=False)
    return await ObjectStorageClient(
        settings.object_storage_service_url
    ).clear_storage_only_bucket(name)


@router.delete(
    "/storage/buckets/{bucket_id}",
    response_model=StorageBucketDeleteResponseDTO,
)
async def admin_panel_delete_storage_bucket(
    bucket_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
) -> StorageBucketDeleteResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketDeleteResponseDTO(deleted=False)
    return await ObjectStorageClient(settings.object_storage_service_url).delete_bucket(
        bucket_id
    )


@router.post(
    "/storage/buckets/{bucket_id}/clear",
    response_model=StorageBucketClearResponseDTO,
)
async def admin_panel_clear_storage_bucket(
    bucket_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
) -> StorageBucketClearResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketClearResponseDTO(cleared=False)
    return await ObjectStorageClient(settings.object_storage_service_url).clear_bucket(
        bucket_id
    )


@router.post(
    "/storage/buckets/{bucket_id}/reconcile",
    response_model=StorageBucketReconcileResponseDTO,
)
async def admin_panel_reconcile_storage_bucket(
    bucket_id: uuid.UUID,
    _: None = Depends(require_admin_panel_key),
) -> StorageBucketReconcileResponseDTO:
    settings = get_settings()
    if not settings.object_storage_service_url:
        return StorageBucketReconcileResponseDTO(found=False, size=0, object_count=0)
    return await ObjectStorageClient(settings.object_storage_service_url).reconcile_bucket(
        bucket_id
    )


@router.get(
    "/storage/scalars",
    response_model=ScalarsListStorageTablesResponseDTO,
)
async def admin_panel_list_scalar_storage(
    _: None = Depends(require_admin_panel_key),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ScalarsListStorageTablesResponseDTO:
    """List ClickHouse tables managed by the scalars service (names, row counts, byte estimates).

    Proxies to ``ScalarsServiceClient.list_storage_tables``. Returns an empty page when
    ``scalars_service_url`` is unset so admin UI can still render.
    """
    settings = get_settings()
    if not settings.scalars_service_url:
        return ScalarsListStorageTablesResponseDTO(
            tables=[], total=0, limit=limit, offset=offset
        )
    return await ScalarsServiceClient(settings.scalars_service_url).list_storage_tables(
        q=q, limit=limit, offset=offset
    )


@router.delete(
    "/storage/scalars/{table_name}",
    response_model=ScalarsDropStorageTableResponseDTO,
)
async def admin_panel_drop_scalar_table(
    table_name: str,
    _: None = Depends(require_admin_panel_key),
) -> ScalarsDropStorageTableResponseDTO:
    """Destructive: drop one scalars-managed ClickHouse table by exact name.

    Intended for broken or leaked tables; validate names in the scalars service before
    executing ``DROP TABLE``.
    """
    settings = get_settings()
    if not settings.scalars_service_url:
        return ScalarsDropStorageTableResponseDTO(dropped=False, table=table_name)
    return await ScalarsServiceClient(settings.scalars_service_url).drop_storage_table(
        table_name
    )
