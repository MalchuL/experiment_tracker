from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from object_storage.db.models import Bucket


def _bucket_scope_filter(project_id: UUID, experiment_id: UUID | None):
    """Match project CAS row (experiment_id NULL) or a specific experiment bucket."""
    if experiment_id is None:
        return (Bucket.project_id == project_id) & (Bucket.experiment_id.is_(None))
    return (Bucket.project_id == project_id) & (Bucket.experiment_id == experiment_id)


class BucketsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> Bucket | None:
        result = await self._session.execute(
            select(Bucket).where(_bucket_scope_filter(project_id, experiment_id))
        )
        return result.scalar_one_or_none()

    async def get_bucket_by_id(self, bucket_id: UUID) -> Bucket | None:
        result = await self._session.execute(select(Bucket).where(Bucket.id == bucket_id))
        return result.scalar_one_or_none()

    async def get_bucket_by_name(self, name: str) -> Bucket | None:
        result = await self._session.execute(select(Bucket).where(Bucket.name == name))
        return result.scalar_one_or_none()

    async def list_all_buckets(self) -> list[Bucket]:
        result = await self._session.execute(select(Bucket).order_by(Bucket.name))
        return list(result.scalars().all())

    async def list_buckets(
        self,
        project_id: UUID | None = None,
        experiment_id: UUID | None = None,
        *,
        name_contains: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[Bucket], int]:
        clauses = []
        if project_id is not None:
            clauses.append(Bucket.project_id == project_id)
        if experiment_id is not None:
            clauses.append(Bucket.experiment_id == experiment_id)
        if name_contains and name_contains.strip():
            clauses.append(Bucket.name.ilike(f"%{name_contains.strip()}%"))
        where = and_(*clauses) if clauses else None
        count_stmt = select(func.count()).select_from(Bucket)
        data_stmt = select(Bucket).order_by(Bucket.created_at.desc())
        if where is not None:
            count_stmt = count_stmt.where(where)
            data_stmt = data_stmt.where(where)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        if limit is not None:
            data_stmt = data_stmt.limit(limit).offset(offset)
        elif offset:
            data_stmt = data_stmt.offset(offset)
        result = await self._session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def create_bucket(self, bucket: Bucket) -> Bucket:
        self._session.add(bucket)
        return bucket

    async def update_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None, **kwargs
    ) -> None:
        await self._session.execute(
            update(Bucket)
            .where(_bucket_scope_filter(project_id, experiment_id))
            .values(**kwargs)
        )

    async def increment_bucket_size(
        self, project_id: UUID, experiment_id: UUID | None = None, size: int = 1
    ) -> None:
        await self._session.execute(
            update(Bucket)
            .where(_bucket_scope_filter(project_id, experiment_id))
            .values(size=Bucket.size + size)
        )
        await self._session.flush()

    async def decrement_bucket_size(
        self, project_id: UUID, experiment_id: UUID | None = None, size: int = 1
    ) -> None:
        await self._session.execute(
            update(Bucket)
            .where(_bucket_scope_filter(project_id, experiment_id))
            .values(size=Bucket.size - size)
        )
        await self._session.flush()

    async def get_all_project_buckets(self, project_id: UUID) -> list[Bucket]:
        result = await self._session.execute(
            select(Bucket).where(Bucket.project_id == project_id)
        )
        return list(result.scalars().all())

    async def delete_bucket(
        self, project_id: UUID, experiment_id: UUID | None = None
    ) -> None:
        await self._session.execute(
            delete(Bucket).where(_bucket_scope_filter(project_id, experiment_id))
        )

    async def delete_bucket_by_id(self, bucket_id: UUID) -> None:
        await self._session.execute(delete(Bucket).where(Bucket.id == bucket_id))

    async def delete_all_project_buckets(self, project_id: UUID) -> None:
        await self._session.execute(
            delete(Bucket).where(Bucket.project_id == project_id)
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def flush(self) -> None:
        await self._session.flush()

    async def refresh(self, instance: object) -> None:
        await self._session.refresh(instance)

    async def rollback(self) -> None:
        await self._session.rollback()
