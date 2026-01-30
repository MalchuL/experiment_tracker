from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import current_active_user
from db.database import get_async_session
from models import User

from .dto import (
    ApiTokenCreateDTO,
    ApiTokenCreateResponseDTO,
    ApiTokenListItemDTO,
    ApiTokenUpdateDTO,
)
from .error import ApiTokenNotFoundError
from .service import ApiTokenService

router = APIRouter(prefix="/users/me/api-tokens", tags=["api-tokens"])


def _raise_api_token_http_error(error: Exception) -> None:
    if isinstance(error, ApiTokenNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=ApiTokenCreateResponseDTO)
async def create_api_token(
    data: ApiTokenCreateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ApiTokenService(session)
    try:
        return await service.create_token(
            user_id=user.id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)


@router.get("", response_model=List[ApiTokenListItemDTO])
async def list_api_tokens(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ApiTokenService(session)
    return await service.list_tokens(user.id)


@router.patch("/{token_id}", response_model=ApiTokenListItemDTO)
async def update_api_token(
    token_id: UUID,
    data: ApiTokenUpdateDTO,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ApiTokenService(session)
    try:
        return await service.update_token(
            user_id=user.id,
            token_id=token_id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)


@router.delete("/{token_id}")
async def revoke_api_token(
    token_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    service = ApiTokenService(session)
    try:
        await service.revoke_token(user_id=user.id, token_id=token_id)
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)
    return {"success": True}
