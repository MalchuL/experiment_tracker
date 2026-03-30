from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
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
