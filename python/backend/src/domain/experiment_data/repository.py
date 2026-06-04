from __future__ import annotations

from collections.abc import Sequence

from lib.db.base_repository import BaseRepository
from lib.types import UUID_TYPE
from models import ExperimentData, ExperimentDataType
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class ExperimentDataRepository(BaseRepository[ExperimentData]):
    """Repository for the generic per-experiment data table.

    Args:
        db: Async SQLAlchemy session used for all queries and mutations.

    Result:
        A repository exposing type-scoped lookup, list, and delete operations
        for ``ExperimentData`` records.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository with its model binding.

        Args:
            db: Async SQLAlchemy session shared with the current request.

        Returns:
            None.
        """
        super().__init__(db, ExperimentData)

    async def get_by_experiment_and_type(
        self, experiment_id: UUID_TYPE, data_type: ExperimentDataType
    ) -> ExperimentData | None:
        """Fetch one experiment-data row by owner experiment and data type.

        Args:
            experiment_id: Experiment UUID that owns the row.
            data_type: Logical data type to fetch, such as ``SNAPSHOT``.

        Returns:
            The matching ``ExperimentData`` row, or ``None`` when the experiment
            has no row for that type.
        """
        stmt = select(ExperimentData).where(
            ExperimentData.experiment_id == experiment_id,
            ExperimentData.type == data_type,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_experiments_and_type(
        self, experiment_ids: Sequence[UUID_TYPE], data_type: ExperimentDataType
    ) -> list[ExperimentData]:
        """Fetch type-specific experiment-data rows for several experiments.

        Args:
            experiment_ids: Experiment UUIDs to include in the query.
            data_type: Logical data type to fetch for each experiment.

        Returns:
            All rows matching the supplied experiments and data type. Returns an
            empty list when ``experiment_ids`` is empty.
        """
        if not experiment_ids:
            return []
        stmt = select(ExperimentData).where(
            ExperimentData.experiment_id.in_(experiment_ids),
            ExperimentData.type == data_type,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_experiment_and_type(
        self, experiment_id: UUID_TYPE, data_type: ExperimentDataType
    ) -> int:
        """Delete one type-specific experiment-data row for an experiment.

        Args:
            experiment_id: Experiment UUID whose row should be removed.
            data_type: Logical data type to delete.

        Returns:
            Number of rows reported deleted by SQLAlchemy.
        """
        stmt = delete(ExperimentData).where(
            ExperimentData.experiment_id == experiment_id,
            ExperimentData.type == data_type,
        )
        result = await self.db.execute(stmt)
        return int(result.rowcount or 0)
