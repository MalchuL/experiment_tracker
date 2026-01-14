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


class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model_type = model
        self.advanced_alchemy_repository = self._create_advanced_alchemy_repository(
            db, model
        )

    class Repository(SQLAlchemyAsyncRepository[T]):
        def __init__(self, model_type: Type[T], *args, **kwargs):
            self.model_type = model_type
            super().__init__(*args, **kwargs)

    def _create_advanced_alchemy_repository(
        self, session: AsyncSession, model: Type[T]
    ) -> SQLAlchemyAsyncRepository[T]:
        repo = self.Repository(
            session=session,
            model_type=model,
        )
        return repo

    async def create(self, obj: T) -> T:
        return await self.advanced_alchemy_repository.add(obj, auto_refresh=True)

    async def update(self, id: str | UUID, **kwargs) -> T:
        # Convert string UUID to UUID object if needed for proper comparison
        from uuid import UUID as UUIDType

        if "id" in kwargs:
            del kwargs["id"]
        existing_obj = await self.get_by_id(id)
        for key, value in kwargs.items():
            setattr(existing_obj, key, value)
        return await self.advanced_alchemy_repository.update(existing_obj)

    async def get_by_id(self, id: str | UUID) -> T:
        try:
            return await self.advanced_alchemy_repository.get_one(
                self.model_type.id == id
            )
        except NotFoundError as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e

    async def upsert(self, obj: T) -> T:
        return await self.advanced_alchemy_repository.upsert(obj, auto_refresh=True)

    async def list(self, options: ListOptions = ListOptions()) -> List[T]:
        return await self.advanced_alchemy_repository.list(
            LimitOffset(offset=options.offset, limit=options.limit)
        )

    async def delete(self, id: str | UUID) -> None:
        try:
            return await self.advanced_alchemy_repository.delete(id)
        except NotFoundError as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e

    async def get_single(self, id: str | UUID) -> T:
        return await self.get_by_id(id)

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        if self.db.in_transaction():
            await self.db.rollback()
