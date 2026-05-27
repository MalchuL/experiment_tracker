"""HTTP routes under ``/users/me/api-tokens``: create, list, update, revoke personal API tokens."""

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
    """Map API token errors to HTTP responses.

    Args:
        error: Exception raised by ``ApiTokenService``.

    Raises:
        HTTPException: ``404`` for unknown tokens and ``400`` for validation,
            persistence, or token state errors.
    """
    if isinstance(error, ApiTokenNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.post("", response_model=ApiTokenCreateResponseDTO)
async def create_api_token(
    data: ApiTokenCreateDTO,
    user: User = Depends(current_active_user),
    api_token_service: ApiTokenService = Depends(get_api_token_service),
):
    """Create a personal API token for the current user.

    Args:
        data: Token name, description, scopes, and optional expiry from the request.
        user: Authenticated user who will own the token.
        api_token_service: API token application service dependency.

    Returns:
        ApiTokenCreateResponseDTO: Token metadata plus the raw token value; the raw
        value is returned only once.

    Raises:
        HTTPException: ``400`` when token creation fails validation or persistence.
    """
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
    """List personal API tokens owned by the current user.

    Args:
        limit: Maximum number of tokens to return.
        offset: Number of tokens to skip.
        user: Authenticated token owner.
        api_token_service: API token application service dependency.

    Returns:
        ApiTokenListResponseDTO: Paginated token metadata without raw token values.
    """
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
    """Update metadata, scopes, or expiry for a personal API token.

    Args:
        token_id: Token identifier to update.
        data: Patch payload with token fields to change.
        user: Authenticated token owner.
        api_token_service: API token application service dependency.

    Returns:
        ApiTokenListItemDTO: Updated token metadata.

    Raises:
        HTTPException: ``404`` when the token is not owned by the user or does not
            exist, and ``400`` for other update errors.
    """
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
    """Revoke a personal API token.

    Args:
        token_id: Token identifier to revoke.
        user: Authenticated token owner.
        api_token_service: API token application service dependency.

    Returns:
        ApiTokenListItemDTO: Revoked token metadata.

    Raises:
        HTTPException: ``404`` when the token is not owned by the user or does not
            exist, and ``400`` for other revoke errors.
    """
    try:
        return await api_token_service.revoke_token(user_id=user.id, token_id=token_id)
    except Exception as exc:  # noqa: BLE001
        _raise_api_token_http_error(exc)
