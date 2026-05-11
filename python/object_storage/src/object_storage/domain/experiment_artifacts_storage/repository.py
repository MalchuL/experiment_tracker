from __future__ import annotations

from typing import Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from object_storage.db.models import ExperimentBlob
from uuid import UUID
from sqlalchemy import delete, func, select


class ExperimentArtifactsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_experiment_blob(
        self, experiment_blob: ExperimentBlob
    ) -> ExperimentBlob:
        self._session.add(experiment_blob)
        return experiment_blob

    async def get_experiment_blob(
        self,
        project_id: UUID,
        experiment_id: UUID,
        *,
        artifact_hash: str | None = None,
        file_path: str | None = None,
        blob_id: UUID | None = None,
    ) -> ExperimentBlob | None:
        if artifact_hash is None and file_path is None and blob_id is None:
            raise ValueError(
                "Provide at least one identifier: artifact_hash, file_path, or blob_id"
            )
        clauses = [
            ExperimentBlob.project_id == project_id,
            ExperimentBlob.experiment_id == experiment_id,
        ]
        if artifact_hash is not None:
            clauses.append(ExperimentBlob.artifact_hash == artifact_hash)
        if file_path is not None:
            clauses.append(ExperimentBlob.file_path == file_path)
        if blob_id is not None:
            clauses.append(ExperimentBlob.id == blob_id)
        result = await self._session.execute(
            select(ExperimentBlob).where(*clauses)
        )
        return result.scalar_one_or_none()

    def _list_blobs_clauses(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file_paths: list[str] | None,
    ) -> list[Any]:
        clauses: list[Any] = [
            ExperimentBlob.project_id == project_id,
            ExperimentBlob.experiment_id == experiment_id,
        ]
        if file_paths:
            clauses.append(ExperimentBlob.file_path.in_(file_paths))
        return clauses

    async def _count_experiment_blobs(
        self,
        project_id: UUID,
        experiment_id: UUID,
        file_paths: list[str] | None = None,
    ) -> int:
        clauses = self._list_blobs_clauses(project_id, experiment_id, file_paths)
        result = await self._session.scalar(
            select(func.count()).select_from(ExperimentBlob).where(*clauses)
        )
        return int(result or 0)

    async def list_experiment_blobs(
        self,
        project_id: UUID,
        experiment_id: UUID,
        limit: int = 100,
        offset: int = 0,
        file_paths: list[str] | None = None,
    ) -> tuple[list[ExperimentBlob], int]:
        """Return a page of blobs and total count matching filters (single query when rows exist)."""

        clauses = self._list_blobs_clauses(project_id, experiment_id, file_paths)

        # Window aggregate: COUNT(*) OVER () counts every row that matches WHERE,
        # before LIMIT/OFFSET (PostgreSQL evaluates window functions after WHERE,
        # then applies ORDER BY / LIMIT / OFFSET). So each selected row carries
        # the same scalar — the full result-set size for this filter — not a
        # per-row running count unless you add PARTITION BY / ORDER BY inside OVER().
        total_over = func.count().over()

        # Second column is that repeated total (aliased for readability in row tuples).
        stmt = (
            select(ExperimentBlob, total_over.label("_total"))
            .where(*clauses)
            .order_by(ExperimentBlob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        if not rows:
            # rows is empty when: (1) nothing matches WHERE (no blobs / path filter
            # misses); or (2) offset is past the last row — LIMIT+OFFSET returns no
            # rows, so we never get _total from the window column. Fall back to COUNT.
            total = await self._count_experiment_blobs(
                project_id, experiment_id, file_paths
            )
            return [], total
        total = int(rows[0][1])
        blobs = [cast(ExperimentBlob, row[0]) for row in rows]
        return blobs, total

    async def delete_experiment_blob(
        self, project_id: UUID, experiment_id: UUID, artifact_hash: str
    ) -> bool:
        result = await self._session.execute(
            delete(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == artifact_hash,
            )
        )
        return cast(int, cast(Any, result).rowcount or 0) > 0

    async def delete_all_experiment_blobs(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        await self._session.execute(
            delete(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
        )

    async def list_tracked_artifact_hashes(
        self, project_id: UUID, experiment_id: UUID
    ) -> list[str]:
        """Return distinct artifact hashes referenced by tracked rows."""

        result = await self._session.execute(
            select(ExperimentBlob.artifact_hash).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
        )
        return [row[0] for row in result.all()]

    async def get_experiment_blob_usage(
        self, project_id: UUID, experiment_id: UUID
    ) -> dict:
        result = await self._session.execute(
            select(func.count(), func.coalesce(func.sum(ExperimentBlob.size), 0)).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
        )
        count, size = result.one()
        return {"count": int(count or 0), "bytes": int(size or 0)}

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, instance: object) -> None:
        await self._session.refresh(instance)

    async def rollback(self) -> None:
        await self._session.rollback()
