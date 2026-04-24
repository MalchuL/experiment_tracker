from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import current_active_user
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User

from .dto import (
    ApiTokenCreateDTO,
    ApiTokenCreateResponseDTO,
    ApiTokenListItemDTO,
    ApiTokenListResponseDTO,
    ApiTokenUpdateDTO,
)
from api.routes.service_dependencies import get_api_token_service
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
    api_token_service: ApiTokenService = Depends(get_api_token_service),
):
    try:
        return await api_token_service.create_token(
            user_id=user.id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)


@router.get("", response_model=ApiTokenListResponseDTO)
async def list_api_tokens(
    limit: int = Query(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_active_user),
    api_token_service: ApiTokenService = Depends(get_api_token_service),
):
    return await api_token_service.list_tokens(
        user.id,
        ListOptions(limit=limit, offset=offset),
    )


@router.patch("/{token_id}", response_model=ApiTokenListItemDTO)
async def update_api_token(
    token_id: UUID,
    data: ApiTokenUpdateDTO,
    user: User = Depends(current_active_user),
    api_token_service: ApiTokenService = Depends(get_api_token_service),
):
    try:
        return await api_token_service.update_token(
            user_id=user.id,
            token_id=token_id,
            name=data.name,
            description=data.description,
            scopes=data.scopes,
            expires_in_days=data.expires_in_days,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)


@router.delete("/{token_id}", response_model=ApiTokenListItemDTO)
async def revoke_api_token(
    token_id: UUID,
    user: User = Depends(current_active_user),
    api_token_service: ApiTokenService = Depends(get_api_token_service),
) -> ApiTokenListItemDTO:
    try:
        return await api_token_service.revoke_token(user_id=user.id, token_id=token_id)
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)
