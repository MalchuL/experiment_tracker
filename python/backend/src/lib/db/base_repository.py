from typing import List, TypeVar, Generic, Optional, Type
from uuid import UUID
from models import Base
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, delete
from typing import Protocol
from sqlalchemy.exc import NoResultFound
from lib.db.error import DBNotFoundError


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
        self.model = model

    async def create(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

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

        stmt = update(self.model).where(self.model.id == id).values(**kwargs)  # type: ignore[arg-type]
        await self.db.execute(stmt)
        await self.db.flush()
        # Return the updated object
        result = await self.db.execute(select(self.model).where(self.model.id == id))  # type: ignore[arg-type]
        try:
            obj = result.scalar_one()
        except NoResultFound as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e
        return obj

    async def get_by_id(self, id: str | UUID) -> T:
        result = await self.db.execute(select(self.model).where(self.model.id == id))  # type: ignore[arg-type]
        try:
            return result.scalar_one()
        except NoResultFound as e:
            raise DBNotFoundError(f"Object with id {id} not found") from e

    async def upsert(self, obj: T) -> T:
        # Check if object exists
        existing = await self.get_by_id(obj.id)  # type: ignore
        if existing:
            # Update existing
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing, key, value)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            # Create new
            return await self.create(obj)

    async def list(self, options: ListOptions = ListOptions()) -> List[T]:
        result = await self.db.execute(
            select(self.model).limit(options.limit).offset(options.offset)
        )
        return list(result.scalars().all())

    async def delete(self, id: str | UUID) -> None:
        await self.get_by_id(id)
        stmt = delete(self.model).where(self.model.id == id)  # type: ignore[arg-type]
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_single(self, id: str | UUID) -> T:
        return await self.get_by_id(id)

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        if self.db.in_transaction():
            await self.db.rollback()
