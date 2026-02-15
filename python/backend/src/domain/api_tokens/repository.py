from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import ApiToken


class ApiTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, token: ApiToken) -> ApiToken:
        self.db.add(token)
        await self.db.refresh(token)
        return token

    async def get_by_id(self, token_id: UUID, user_id: UUID) -> Optional[ApiToken]:
        result = await self.db.execute(
            select(ApiToken)
            .where(ApiToken.id == token_id, ApiToken.user_id == user_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> List[ApiToken]:
        result = await self.db.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_hash(self, token_hash: str) -> Optional[ApiToken]:
        result = await self.db.execute(
            select(ApiToken)
            .options(selectinload(ApiToken.user))
            .where(ApiToken.token_hash == token_hash)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, token: ApiToken) -> ApiToken:
        self.db.add(token)
        await self.db.refresh(token)
        return token
