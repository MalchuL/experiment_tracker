"""Database repository for CAS metadata operations."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from object_storage.db.models import Blob, Experiment, Snapshot


class ObjectStorageRepository:
    """Repository for reading/writing CAS metadata in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an active async session."""

        self._session = session

    async def fetch_existing_blob_hashes(self, hashes: Iterable[str]) -> set[str]:
        """Return the subset of hashes that already exist in the blobs table."""

        if not hashes:
            return set()
        result = await self._session.execute(select(Blob.hash).where(Blob.hash.in_(hashes)))
        return {row[0] for row in result.all()}

    async def fetch_blob(self, blob_hash: str) -> Blob | None:
        """Fetch a blob by hash, or return None if it is absent."""

        return await self._session.get(Blob, blob_hash)

    async def add_blob(self, blob_hash: str, size: int) -> None:
        """Stage a new blob record for insert in the current session."""

        self._session.add(Blob(hash=blob_hash, size=size, ref_count=0))

    async def get_or_create_experiment(self, name: str) -> Experiment:
        """Fetch an experiment by name, creating it if it does not exist."""

        result = await self._session.execute(select(Experiment).where(Experiment.name == name))
        experiment = result.scalars().first()
        if experiment is None:
            experiment = Experiment(name=name)
            self._session.add(experiment)
            await self._session.flush()
        return experiment

    async def create_snapshot(self, experiment_id: UUID, manifest: list[dict]) -> Snapshot:
        """Stage a new snapshot for the given experiment and manifest."""

        snapshot = Snapshot(experiment_id=experiment_id, manifest=manifest)
        self._session.add(snapshot)
        return snapshot

    async def increment_blob_ref_counts(self, hashes: Iterable[str]) -> None:
        """Increment reference counts for blobs attached to a snapshot."""

        if not hashes:
            return
        await self._session.execute(
            update(Blob)
            .where(Blob.hash.in_(hashes))
            .values(ref_count=Blob.ref_count + 1)
        )

    async def fetch_snapshot(self, snapshot_id: UUID) -> Snapshot | None:
        """Return a snapshot by id, or None if it does not exist."""

        result = await self._session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
        return result.scalars().first()

    async def commit(self) -> None:
        """Commit the current transaction to persist staged changes."""

        await self._session.commit()

    async def refresh(self, instance: object) -> None:
        """Refresh an instance from the database after commit."""

        await self._session.refresh(instance)

    async def rollback(self) -> None:
        """Rollback the current transaction after an error."""

        await self._session.rollback()
