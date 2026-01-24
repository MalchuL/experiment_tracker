from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from models import User

from .dto import (
    TeamCreateDTO,
    TeamMemberCreateDTO,
    TeamMemberDeleteDTO,
    TeamMemberReadDTO,
    TeamMemberUpdateDTO,
    TeamReadDTO,
    TeamUpdateDTO,
)
from .errors import (
    TeamAccessDeniedError,
    TeamMemberAlreadyExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from .service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


def _raise_team_http_error(error: Exception) -> None:
    if isinstance(error, TeamAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, (TeamNotFoundError, TeamMemberNotFoundError)):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, TeamMemberAlreadyExistsError):
        raise HTTPException(status_code=409, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=TeamReadDTO)
async def create_team(
    data: TeamCreateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        return await service.create_team(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.patch("", response_model=TeamReadDTO)
async def update_team(
    data: TeamUpdateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        return await service.update_team(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


# Member routes MUST come before /{team_id} route to avoid routing conflicts
@router.post("/members", response_model=TeamMemberReadDTO)
async def add_team_member(
    data: TeamMemberCreateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        return await service.add_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.patch("/members", response_model=TeamMemberReadDTO)
async def update_team_member(
    data: TeamMemberUpdateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        return await service.update_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)


@router.delete("/members")
async def remove_team_member(
    data: TeamMemberDeleteDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        await service.remove_team_member(user.id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)
    return {"success": True}


@router.delete("/{team_id}")
async def delete_team(
    team_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = TeamService(session)
    try:
        await service.delete_team(user.id, team_id)
    except Exception as exc:  # noqa: BLE001
        _raise_team_http_error(exc)
    return {"success": True}
