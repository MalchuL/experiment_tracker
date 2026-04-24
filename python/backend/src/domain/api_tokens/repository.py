from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from models import ApiToken


class ApiTokenRepository:
    """Persistence for API tokens; uses Advanced Alchemy for paginated listing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._aa = BaseRepository(db, ApiToken)

    async def create(self, token: ApiToken) -> ApiToken:
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def get_by_id(self, token_id: UUID, user_id: UUID) -> Optional[ApiToken]:
        result = await self.db.execute(
            select(ApiToken)
            .where(ApiToken.id == token_id, ApiToken.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, list_options: ListOptions | None = None
    ) -> Page[ApiToken]:
        return await self._aa.list(
            ApiToken.user_id == user_id,
            order_by=ApiToken.created_at.desc(),
            list_options=list_options,
        )

    async def get_by_hash(self, token_hash: str) -> Optional[ApiToken]:
        result = await self.db.execute(
            select(ApiToken)
            .options(selectinload(ApiToken.user))
            .where(ApiToken.token_hash == token_hash)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, token: ApiToken) -> ApiToken:
        self.db.merge(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token
