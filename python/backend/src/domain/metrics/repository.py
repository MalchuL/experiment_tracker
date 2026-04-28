from typing import List, Tuple
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from models import Experiment, Metric
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from lib.types import UUID_TYPE
from sqlalchemy.orm import selectinload


class MetricRepository(BaseRepository[Metric]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Metric)

    async def get_metrics_by_experiment(
        self,
        experiment_id: UUID_TYPE | list[UUID_TYPE],
        full_load: bool = False,
        list_options: ListOptions | None = None,
    ) -> Page[Metric]:
        if isinstance(experiment_id, (list, tuple)):
            scope = Metric.experiment_id.in_(experiment_id)
        else:
            scope = Metric.experiment_id == experiment_id
        load = [selectinload(Metric.experiment)] if full_load else []
        return await self.list(
            scope,
            order_by=Metric.created_at.desc(),
            load=load or None,
            list_options=list_options,
        )

    def _label_clause(self, label: str | None):
        """Match metrics.label: None or '' means SQL NULL; otherwise exact string."""
        if label is None or label == "":
            return Metric.label.is_(None)
        return Metric.label == label

    async def list_distinct_labels_in_project(
        self, project_id: UUID_TYPE
    ) -> tuple[list[str], bool]:
        """Return (sorted non-null labels, has_any_null_label)."""
        stmt = (
            select(Metric.label)
            .join(Experiment, Metric.experiment_id == Experiment.id)
            .where(Experiment.project_id == project_id)
            .distinct()
        )
        res = await self.db.execute(stmt)
        raw = [row[0] for row in res.all()]
        has_unlabeled = any(x is None for x in raw)
        labels = sorted(s for s in raw if s is not None)
        return labels, has_unlabeled

    async def list_unique_name_label_in_project(
        self, project_id: UUID_TYPE
    ) -> list[Tuple[str, str | None]]:
        stmt = (
            select(Metric.name, Metric.label)
            .join(Experiment, Metric.experiment_id == Experiment.id)
            .where(Experiment.project_id == project_id)
            .distinct()
        )
        res = await self.db.execute(stmt)
        rows = list(res.all())
        rows.sort(key=lambda r: (r[0], r[1] is None, r[1] or ""))
        return [(r[0], r[1]) for r in rows]

    async def list_distinct_metric_names_for_label_in_project(
        self, project_id: UUID_TYPE, label: str | None
    ) -> list[str]:
        stmt = (
            select(Metric.name)
            .join(Experiment, Metric.experiment_id == Experiment.id)
            .where(
                and_(
                    Experiment.project_id == project_id,
                    self._label_clause(label),
                )
            )
            .distinct()
        )
        res = await self.db.execute(stmt)
        return sorted(r[0] for r in res.all())

    async def get_by_experiment_name_and_label(
        self,
        experiment_id: UUID_TYPE,
        name: str,
        label: str | None,
    ) -> Metric | None:
        """At most one row per (experiment, name, label); see DB partial unique indexes on `Metric`."""
        stmt = select(Metric).where(
            and_(
                Metric.experiment_id == experiment_id,
                Metric.name == name,
                self._label_clause(label),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_metrics_for_project_label(
        self, project_id: UUID_TYPE, label: str | None
    ) -> list[Metric]:
        """All metric rows in project for this label (for picking latest in Python)."""
        stmt = (
            select(Metric)
            .join(Experiment, Metric.experiment_id == Experiment.id)
            .where(
                and_(
                    Experiment.project_id == project_id,
                    self._label_clause(label),
                )
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
