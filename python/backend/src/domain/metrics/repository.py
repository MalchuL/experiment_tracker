from typing import List, Sequence, Tuple
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from models import Experiment, Metric
from sqlalchemy import and_, or_, select
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

    async def list_selective_project_metrics(
        self,
        project_id: UUID_TYPE,
        metric_keys: Sequence[tuple[str, str | None]],
        experiment_ids: Sequence[UUID_TYPE] | None = None,
    ) -> list[Metric]:
        """Load exact metric dimensions from experiments in one project.

        Purpose:
            Provide a bounded query primitive for selective metric and top-k
            services without changing the existing project metric repository paths.

        Args:
            project_id: Project that must own every returned experiment.
            metric_keys: Exact ``(name, label)`` dimensions. ``None`` matches only
                database ``NULL`` labels.
            experiment_ids: Optional experiment filter. Missing and foreign-project
                identifiers naturally produce no rows.

        Returns:
            list[Metric]: Matching metric rows ordered by creation time descending.
                An empty key or experiment selection returns an empty list.
        """
        if not metric_keys or (experiment_ids is not None and not experiment_ids):
            return []
        key_clauses = [
            and_(Metric.name == name, self._label_clause(label))
            for name, label in metric_keys
        ]
        filters = [
            Experiment.project_id == project_id,
            or_(*key_clauses),
        ]
        if experiment_ids is not None:
            filters.append(Metric.experiment_id.in_(experiment_ids))
        stmt = (
            select(Metric)
            .join(Experiment, Metric.experiment_id == Experiment.id)
            .where(and_(*filters))
            .order_by(Metric.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
