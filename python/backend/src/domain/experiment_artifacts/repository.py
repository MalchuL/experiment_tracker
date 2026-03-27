from __future__ import annotations

from typing import cast
from uuid import UUID

from lib.db.base_repository import BaseRepository
from models import ExperimentArtifact
from sqlalchemy.engine import CursorResult
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class ExperimentArtifactRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExperimentArtifact)

    async def get_by_identity(
        self,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> ExperimentArtifact | None:
        result = await self.db.execute(
            select(ExperimentArtifact).where(
                ExperimentArtifact.experiment_id == experiment_id,
                ExperimentArtifact.name == name,
                ExperimentArtifact.filepath == filepath,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_name(
        self,
        experiment_id: UUID,
        name: str,
    ) -> list[ExperimentArtifact]:
        result = await self.db.execute(
            select(ExperimentArtifact)
            .where(
                ExperimentArtifact.experiment_id == experiment_id,
                ExperimentArtifact.name == name,
            )
            .order_by(ExperimentArtifact.filepath.asc())
        )
        return list(result.scalars().all())

    async def list_by_experiment(
        self,
        experiment_id: UUID,
        names: list[str] | None = None,
    ) -> list[ExperimentArtifact]:
        stmt = (
            select(ExperimentArtifact)
            .where(ExperimentArtifact.experiment_id == experiment_id)
            .order_by(ExperimentArtifact.name.asc(), ExperimentArtifact.filepath.asc())
        )
        if names:
            stmt = stmt.where(ExperimentArtifact.name.in_(names))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_identity(
        self,
        experiment_id: UUID,
        name: str,
        filepath: str,
    ) -> int:
        result = await self.db.execute(
            delete(ExperimentArtifact).where(
                ExperimentArtifact.experiment_id == experiment_id,
                ExperimentArtifact.name == name,
                ExperimentArtifact.filepath == filepath,
            )
        )
        cursor_result = cast(CursorResult, result)
        return int(cursor_result.rowcount or 0)

    async def delete_by_name(
        self,
        experiment_id: UUID,
        name: str,
    ) -> int:
        result = await self.db.execute(
            delete(ExperimentArtifact).where(
                ExperimentArtifact.experiment_id == experiment_id,
                ExperimentArtifact.name == name,
            )
        )
        cursor_result = cast(CursorResult, result)
        return int(cursor_result.rowcount or 0)
