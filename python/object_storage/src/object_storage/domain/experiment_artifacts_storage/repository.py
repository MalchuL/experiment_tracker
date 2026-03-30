from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from object_storage.db.models import ExperimentBlob
from uuid import UUID
from sqlalchemy import select
from sqlalchemy import delete


class ExperimentArtifactsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_experiment_blob(
        self, experiment_blob: ExperimentBlob
    ) -> ExperimentBlob:
        self._session.add(experiment_blob)
        return experiment_blob

    async def get_experiment_blob(
        self, project_id: UUID, experiment_id: UUID, artifact_hash: str
    ) -> ExperimentBlob | None:
        result = await self._session.execute(
            select(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
                ExperimentBlob.artifact_hash == artifact_hash,
            )
        )
        return result.scalar_one_or_none()

    async def list_experiment_blobs(
        self,
        project_id: UUID,
        experiment_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExperimentBlob]:
        result = await self._session.execute(
            select(ExperimentBlob)
            .where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

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
        return result.rowcount > 0

    async def delete_all_experiment_blobs(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        result = await self._session.execute(
            delete(ExperimentBlob).where(
                ExperimentBlob.project_id == project_id,
                ExperimentBlob.experiment_id == experiment_id,
            )
        )
        return result.rowcount > 0

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, instance: object) -> None:
        await self._session.refresh(instance)

    async def rollback(self) -> None:
        await self._session.rollback()
