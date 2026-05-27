import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from experiment_tracker_shared import utc_now_naive

from models import ApiToken, User

from lib.pagination import ListOptions

from .dto import (
    ApiTokenCreateResponseDTO,
    ApiTokenListItemDTO,
    ApiTokenListResponseDTO,
)
from .repository import ApiTokenRepository
from .error import (
    ApiTokenExpiredError,
    ApiTokenInvalidError,
    ApiTokenNotFoundError,
    ApiTokenRevokedError,
)
from .mapper import ApiTokenMapper

logger = logging.getLogger("api_tokens")


def generate_raw_token() -> str:
    """Generate a new opaque personal-access-token string.

    Args:
        None.

    Returns:
        str: A URL-safe token prefixed with ``pat_`` for client display and later
        authentication.
    """
    return f"pat_{secrets.token_urlsafe(32)}"


def hash_token(raw_token: str) -> str:
    """Hash a raw token for storage and lookup.

    Args:
        raw_token: Client-visible token value.

    Returns:
        str: SHA-256 hex digest used as the database key.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedToken:
    """Cached API-token validation result.

    Args:
        token_id: Token row identifier.
        user_id: User associated with the token.
        scopes: Scopes encoded on the token.
        expires_at: Optional token expiry timestamp.
        revoked: Whether the token was revoked when cached.
        expires_at_ts: Cache-entry expiry timestamp expressed as ``time.time()``.
    """

    token_id: UUID
    user_id: UUID
    scopes: list[str]
    expires_at: Optional[datetime]
    revoked: bool
    expires_at_ts: float


class TokenCache:
    """Short-lived in-process cache for validated token metadata.

    The cache avoids repeated database lookups during API-token authentication while
    keeping a small TTL so revocation and expiry are eventually observed.
    """

    def __init__(self, ttl_seconds: int = 60):
        """Initialize the token cache.

        Args:
            ttl_seconds: Number of seconds a cached validation entry remains valid.
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CachedToken] = {}

    def get(self, token_hash: str) -> Optional[CachedToken]:
        """Return a cached token entry if present and not expired.

        Args:
            token_hash: SHA-256 digest of the raw token.

        Returns:
            Optional[CachedToken]: Cached token metadata, or ``None`` when missing or
            expired.
        """
        cached = self._cache.get(token_hash)
        if cached is None:
            return None
        if cached.expires_at_ts < time.time():
            self._cache.pop(token_hash, None)
            return None
        return cached

    def set(self, token_hash: str, token: CachedToken) -> None:
        """Store token metadata in the cache.

        Args:
            token_hash: SHA-256 digest of the raw token.
            token: Cached token metadata including the cache expiry timestamp.

        Returns:
            None: The entry is stored in memory.
        """
        self._cache[token_hash] = token

    def invalidate(self, token_hash: str) -> None:
        """Remove one token entry from the cache.

        Args:
            token_hash: SHA-256 digest to remove.

        Returns:
            None: The entry is removed if present.
        """
        self._cache.pop(token_hash, None)


TOKEN_CACHE = TokenCache()


class ApiTokenService:
    """Application service for personal API tokens.

    The service issues raw tokens once, stores only hashes, validates token state for
    API-token authentication, updates last-used timestamps, and commits successful
    token mutations through the injected database session.
    """

    def __init__(self, db: AsyncSession, api_token_repository: ApiTokenRepository):
        self.db = db
        self.api_token_repository = api_token_repository
        self.mapper = ApiTokenMapper()

    async def create_token(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str],
        scopes: list[str],
        expires_in_days: Optional[int],
    ) -> ApiTokenCreateResponseDTO:
        """Create and persist a new personal API token.

        Args:
            user_id: Owner of the token.
            name: Human-readable token name.
            description: Optional description shown in token lists.
            scopes: Permission scopes encoded on the token.
            expires_in_days: Optional number of days until expiry.

        Returns:
            ApiTokenCreateResponseDTO: Token metadata plus the one-time raw token.
        """
        raw_token = generate_raw_token()
        token_hash = hash_token(raw_token)
        expires_at = (
            utc_now_naive() + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        )
        token = ApiToken(
            user_id=user_id,
            token_hash=token_hash,
            name=name,
            description=description,
            scopes=scopes,
            expires_at=expires_at,
        )
        token = await self.api_token_repository.create(token)
        logger.info(
            "api_token_created",
            extra={
                "token_id": str(token.id),
                "user_id": str(user_id),
                "scopes": scopes,
            },
        )
        await self.db.commit()
        return self.mapper.token_schema_to_create_response_dto(token, raw_token)

    async def list_tokens(
        self, user_id: UUID, list_options: ListOptions = ListOptions()
    ) -> ApiTokenListResponseDTO:
        """List token metadata for one user.

        Args:
            user_id: Token owner.
            list_options: Pagination limit and offset.

        Returns:
            ApiTokenListResponseDTO: Paginated tokens without raw token values.
        """
        tokens_page = await self.api_token_repository.list_by_user(user_id, list_options)
        return ApiTokenListResponseDTO.from_page(
            tokens_page.map(self.mapper.token_schema_to_list_item_dto)
        )

    async def update_token(
        self,
        user_id: UUID,
        token_id: UUID,
        name: Optional[str],
        description: Optional[str],
        scopes: Optional[list[str]],
        expires_in_days: Optional[int],
    ) -> ApiTokenListItemDTO:
        """Update editable token metadata and expiry.

        Args:
            user_id: Owner of the token.
            token_id: Token identifier.
            name: Optional replacement name.
            description: Optional replacement description.
            scopes: Optional replacement scope list.
            expires_in_days: Optional expiry extension from the current time.

        Returns:
            ApiTokenListItemDTO: Updated token metadata.

        Raises:
            ApiTokenNotFoundError: If the token does not exist for ``user_id``.
        """
        token = await self.api_token_repository.get_by_id(token_id, user_id)
        if token is None:
            raise ApiTokenNotFoundError("Token not found")
        if name is not None:
            token.name = name
        if description is not None:
            token.description = description
        if scopes is not None:
            token.scopes = scopes
        if expires_in_days is not None:
            token.expires_at = utc_now_naive() + timedelta(days=expires_in_days)
        token = await self.api_token_repository.update(token)
        logger.info(
            "api_token_updated",
            extra={"token_id": str(token.id), "user_id": str(user_id)},
        )
        await self.db.commit()
        return self.mapper.token_schema_to_list_item_dto(token)

    async def revoke_token(self, user_id: UUID, token_id: UUID) -> ApiTokenListItemDTO:
        """Mark a token as revoked.

        Args:
            user_id: Owner of the token.
            token_id: Token identifier.

        Returns:
            ApiTokenListItemDTO: Revoked token metadata.

        Raises:
            ApiTokenNotFoundError: If the token does not exist for ``user_id``.
        """
        token = await self.api_token_repository.get_by_id(token_id, user_id)
        if token is None:
            raise ApiTokenNotFoundError("Token not found")
        token.revoked = True
        token = await self.api_token_repository.update(token)
        logger.info(
            "api_token_revoked",
            extra={"token_id": str(token.id), "user_id": str(user_id)},
        )
        await self.db.commit()
        return self.mapper.token_schema_to_list_item_dto(token)

    async def validate_token(self, raw_token: str) -> ApiToken:
        """Validate a raw API token and return its database row.

        Args:
            raw_token: Token value supplied by a client.

        Returns:
            ApiToken: Active, unexpired token row.

        Raises:
            ApiTokenInvalidError: If the token hash is unknown or mismatched.
            ApiTokenRevokedError: If the token has been revoked.
            ApiTokenExpiredError: If the token expiry time has passed.
        """
        token_hash = hash_token(raw_token)
        cached = TOKEN_CACHE.get(token_hash)
        if cached:
            if cached.revoked:
                raise ApiTokenRevokedError("Token revoked")
            if cached.expires_at and cached.expires_at <= utc_now_naive():
                raise ApiTokenExpiredError("Token expired")
            token = await self.api_token_repository.get_by_hash(token_hash)
            if token is None or not hmac.compare_digest(token.token_hash, token_hash):
                raise ApiTokenInvalidError("Token invalid")
            return token

        token = await self.api_token_repository.get_by_hash(token_hash)
        if token is None or not hmac.compare_digest(token.token_hash, token_hash):
            raise ApiTokenInvalidError("Token invalid")
        if token.revoked:
            raise ApiTokenRevokedError("Token revoked")
        if token.expires_at and token.expires_at <= utc_now_naive():
            raise ApiTokenExpiredError("Token expired")

        TOKEN_CACHE.set(
            token_hash,
            CachedToken(
                token_id=token.id,
                user_id=token.user_id,
                scopes=token.scopes or [],
                expires_at=token.expires_at,
                revoked=token.revoked,
                expires_at_ts=time.time() + TOKEN_CACHE.ttl_seconds,
            ),
        )
        return token

    async def mark_used(self, token: ApiToken) -> None:
        """Persist a token's last-used timestamp.

        Args:
            token: Token row that was successfully used for authentication.

        Returns:
            None: The database row is updated and committed.
        """
        token.last_used_at = utc_now_naive()
        await self.api_token_repository.update(token)
        logger.info(
            "api_token_used",
            extra={"token_id": str(token.id), "user_id": str(token.user_id)},
        )
        await self.db.commit()

    async def get_user_for_token(self, raw_token: str) -> User:
        """Resolve a raw API token to its active user.

        Args:
            raw_token: Token value supplied by a client.

        Returns:
            User: User associated with the valid token.

        Raises:
            ApiTokenInvalidError: If validation fails or the token has no user row.
            ApiTokenRevokedError: If the token is revoked.
            ApiTokenExpiredError: If the token is expired.
        """
        token = await self.validate_token(raw_token)
        await self.mark_used(token)
        if token.user is None:
            raise ApiTokenInvalidError("Token user not found")
        return token.user
