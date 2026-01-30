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

from models import ApiToken, User, utc_now

from .dto import ApiTokenCreateResponseDTO, ApiTokenListItemDTO
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
    return f"pat_{secrets.token_urlsafe(32)}"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedToken:
    token_id: UUID
    user_id: UUID
    scopes: list[str]
    expires_at: Optional[datetime]
    revoked: bool
    expires_at_ts: float


class TokenCache:
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CachedToken] = {}

    def get(self, token_hash: str) -> Optional[CachedToken]:
        cached = self._cache.get(token_hash)
        if cached is None:
            return None
        if cached.expires_at_ts < time.time():
            self._cache.pop(token_hash, None)
            return None
        return cached

    def set(self, token_hash: str, token: CachedToken) -> None:
        self._cache[token_hash] = token

    def invalidate(self, token_hash: str) -> None:
        self._cache.pop(token_hash, None)


TOKEN_CACHE = TokenCache()


class ApiTokenService:
    def __init__(self, db: AsyncSession, auto_commit: bool = True):
        self.db = db
        self.repo = ApiTokenRepository(db, auto_commit=auto_commit)
        self.auto_commit = auto_commit
        self.mapper = ApiTokenMapper()

    async def create_token(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str],
        scopes: list[str],
        expires_in_days: Optional[int],
    ) -> ApiTokenCreateResponseDTO:
        raw_token = generate_raw_token()
        token_hash = hash_token(raw_token)
        expires_at = (
            utc_now() + timedelta(days=expires_in_days)
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
        token = await self.repo.create(token)
        logger.info(
            "api_token_created",
            extra={
                "token_id": str(token.id),
                "user_id": str(user_id),
                "scopes": scopes,
            },
        )
        return self.mapper.token_schema_to_create_response_dto(token, raw_token)

    async def list_tokens(self, user_id: UUID) -> list[ApiTokenListItemDTO]:
        tokens = await self.repo.list_by_user(user_id)
        return self.mapper.token_schema_list_to_list_item_dto(tokens)

    async def update_token(
        self,
        user_id: UUID,
        token_id: UUID,
        name: Optional[str],
        description: Optional[str],
        scopes: Optional[list[str]],
        expires_in_days: Optional[int],
    ) -> ApiTokenListItemDTO:
        token = await self.repo.get_by_id(token_id, user_id)
        if token is None:
            raise ApiTokenNotFoundError("Token not found")
        if name is not None:
            token.name = name
        if description is not None:
            token.description = description
        if scopes is not None:
            token.scopes = scopes
        if expires_in_days is not None:
            token.expires_at = utc_now() + timedelta(days=expires_in_days)
        token = await self.repo.update(token)
        logger.info(
            "api_token_updated",
            extra={"token_id": str(token.id), "user_id": str(user_id)},
        )
        return self.mapper.token_schema_to_list_item_dto(token)

    async def revoke_token(self, user_id: UUID, token_id: UUID) -> ApiTokenListItemDTO:
        token = await self.repo.get_by_id(token_id, user_id)
        if token is None:
            raise ApiTokenNotFoundError("Token not found")
        token.revoked = True
        token = await self.repo.update(token)
        logger.info(
            "api_token_revoked",
            extra={"token_id": str(token.id), "user_id": str(user_id)},
        )
        return self.mapper.token_schema_to_list_item_dto(token)

    async def validate_token(self, raw_token: str) -> ApiToken:
        token_hash = hash_token(raw_token)
        cached = TOKEN_CACHE.get(token_hash)
        if cached:
            if cached.revoked:
                raise ApiTokenRevokedError("Token revoked")
            if cached.expires_at and cached.expires_at <= utc_now():
                raise ApiTokenExpiredError("Token expired")
            token = await self.repo.get_by_hash(token_hash)
            if token is None or not hmac.compare_digest(token.token_hash, token_hash):
                raise ApiTokenInvalidError("Token invalid")
            return token

        token = await self.repo.get_by_hash(token_hash)
        if token is None or not hmac.compare_digest(token.token_hash, token_hash):
            raise ApiTokenInvalidError("Token invalid")
        if token.revoked:
            raise ApiTokenRevokedError("Token revoked")
        if token.expires_at and token.expires_at <= utc_now():
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
        token.last_used_at = utc_now()
        await self.repo.update(token)
        logger.info(
            "api_token_used",
            extra={"token_id": str(token.id), "user_id": str(token.user_id)},
        )

    async def get_user_for_token(self, raw_token: str) -> User:
        token = await self.validate_token(raw_token)
        await self.mark_used(token)
        if token.user is None:
            raise ApiTokenInvalidError("Token user not found")
        return token.user
