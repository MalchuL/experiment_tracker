from typing import List, TypeVar, Generic, Optional, Type
from uuid import UUID
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.filters import LimitOffset
from models import Base
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, delete
from typing import Protocol
from sqlalchemy.exc import NoResultFound
from lib.db.error import DBNotFoundError
from advanced_alchemy.repository import SQLAlchemyAsyncRepository


class HasId(Protocol):
    @property
    def id(self) -> UUID:
        pass


T = TypeVar("T", bound=HasId)


class ListOptions(BaseModel):
    limit: int = 100
    offset: int = 0


class BaseRepository(SQLAlchemyAsyncRepository[T]):
    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model_type = model
        super().__init__(session=db)

    async def create(self, obj: T) -> T:
        return await self.add(obj, auto_refresh=True)

    async def update(self, id: str | UUID, **kwargs) -> T:
        # Convert string UUID to UUID object if needed for proper comparison
        from uuid import UUID as UUIDType

        if isinstance(id, str):
            try:
                id = UUIDType(id)
            except (ValueError, AttributeError):
                pass  # Keep as string if conversion fails
        if "id" in kwargs:
            del kwargs["id"]
        existing_obj = await self.get_by_id(id)
        for key, value in kwargs.items():
            setattr(existing_obj, key, value)
        return await super().update(existing_obj)

    async def get_by_id(self, id: str | UUID) -> T:
        try:
            return await super().get_one(self.model_type.id == id)
        except NotFoundError as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e

    async def upsert(self, obj: T) -> T:
        return await super().upsert(obj, auto_refresh=True)

    async def list(self, options: ListOptions = ListOptions()) -> List[T]:
        return await super().list(
            LimitOffset(offset=options.offset, limit=options.limit)
        )

    async def delete(self, id: str | UUID) -> None:
        try:
            return await super().delete(id)
        except NotFoundError as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e

    async def get_single(self, id: str | UUID) -> T:
        return await self.get_by_id(id)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session.in_transaction():
            await self.session.rollback()
