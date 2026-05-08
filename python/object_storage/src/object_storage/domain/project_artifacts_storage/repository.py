"""Database repository for CAS metadata operations."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from object_storage.db.models import ProjectBlob, Snapshot


class ObjectStorageRepository:
    """Repository for reading/writing CAS metadata in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an active async session."""

        self._session = session

    async def fetch_existing_blob_hashes(
        self, project_id: UUID, hashes: Iterable[str]
    ) -> set[str]:
        """Return the subset of hashes that already exist in the blobs table."""

        if not hashes:
            return set()
        result = await self._session.execute(
            select(ProjectBlob.hash).where(
                ProjectBlob.project_id == project_id, ProjectBlob.hash.in_(hashes)
            )
        )
        return {row[0] for row in result.all()}

    async def fetch_blob(self, project_id: UUID, blob_hash: str) -> ProjectBlob | None:
        """Fetch a blob by hash, or return None if it is absent."""

        return await self._session.get(ProjectBlob, (blob_hash, project_id))

    async def add_blob(
        self,
        project_id: UUID,
        blob_hash: str,
        size: int,
        mime_type: str = "application/octet-stream",
    ) -> None:
        """Stage a new blob record for insert in the current session."""

        self._session.add(
            ProjectBlob(
                project_id=project_id,
                hash=blob_hash,
                mime_type=mime_type,
                size=size,
                ref_count=0,
            )
        )

    async def create_snapshot(self, project_id: UUID, manifest: list[dict]) -> Snapshot:
        """Stage a new snapshot for the given manifest."""

        snapshot = Snapshot(project_id=project_id, manifest=manifest)
        self._session.add(snapshot)
        return snapshot

    async def increment_blob_ref_counts(
        self, project_id: UUID, hashes: Iterable[str]
    ) -> None:
        """Increment reference counts for blobs attached to a snapshot."""

        if not hashes:
            return
        await self._session.execute(
            update(ProjectBlob)
            .where(ProjectBlob.project_id == project_id, ProjectBlob.hash.in_(hashes))
            .values(ref_count=ProjectBlob.ref_count + 1)
        )

    async def decrement_blob_ref_counts(
        self, project_id: UUID, hashes: Iterable[str]
    ) -> None:
        """Decrement reference counts for blobs attached to a snapshot."""

        if not hashes:
            return
        await self._session.execute(
            update(ProjectBlob)
            .where(ProjectBlob.project_id == project_id, ProjectBlob.hash.in_(hashes))
            .values(ref_count=ProjectBlob.ref_count - 1)
        )

    async def fetch_snapshot(self, snapshot_id: UUID) -> Snapshot | None:
        """Return a snapshot by id, or None if it does not exist."""

        result = await self._session.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        return result.scalars().first()

    async def delete_snapshot(self, snapshot_id: UUID) -> bool:
        """Delete a snapshot by id."""

        snapshot = await self.fetch_snapshot(snapshot_id)
        if snapshot is None:
            return False
        await self._session.delete(snapshot)
        return True

    async def commit(self) -> None:
        """Commit the current transaction to persist staged changes."""

        await self._session.commit()

    async def refresh(self, instance: object) -> None:
        """Refresh an instance from the database after commit."""

        await self._session.refresh(instance)

    async def rollback(self) -> None:
        """Rollback the current transaction after an error."""

        await self._session.rollback()

    async def delete_blob(self, project_id: UUID, blob_hash: str) -> bool:
        """Delete one tracked blob metadata row by (project_id, hash)."""

        blob = await self.fetch_blob(project_id, blob_hash)
        if blob is None:
            return False
        await self._session.delete(blob)
        return True

    async def delete_all_blobs(self, project_id: UUID) -> None:
        """Delete all blobs for a project."""

        await self._session.execute(
            delete(ProjectBlob).where(ProjectBlob.project_id == project_id)
        )

    async def delete_all_snapshots(self, project_id: UUID) -> None:
        """Delete all snapshots for a project."""

        await self._session.execute(
            delete(Snapshot).where(Snapshot.project_id == project_id)
        )

    async def get_project_blob_usage(self, project_id: UUID) -> dict:
        result = await self._session.execute(
            select(func.count(), func.coalesce(func.sum(ProjectBlob.size), 0)).where(
                ProjectBlob.project_id == project_id
            )
        )
        count, size = result.one()
        ref_result = await self._session.execute(
            select(func.count(), func.coalesce(func.sum(ProjectBlob.size), 0)).where(
                ProjectBlob.project_id == project_id,
                ProjectBlob.ref_count > 0,
            )
        )
        ref_count, ref_size = ref_result.one()
        snapshots = await self._session.scalar(
            select(func.count()).select_from(Snapshot).where(Snapshot.project_id == project_id)
        )
        return {
            "projectArtifacts": {"count": int(count or 0), "bytes": int(size or 0)},
            "snapshots": {
                "count": int(snapshots or 0),
                "referencedBlobCount": int(ref_count or 0),
                "bytes": int(ref_size or 0),
            },
        }
