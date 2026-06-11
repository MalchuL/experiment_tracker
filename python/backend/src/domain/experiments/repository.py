from typing import List, Literal, Sequence

from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from lib.types import UUID_TYPE
from models import Experiment
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.protocols.user_protocol import UserProtocol
from sqlalchemy.orm import defer, selectinload


LoadOptions = Sequence[Literal["project", "metrics"]] | bool


def _escape_sql_like_metacharacters(fragment: str) -> str:
    """Escape ``%``, ``_``, and ``\\`` for use in ``LIKE`` / ``ILIKE`` with ``ESCAPE '\\'``."""

    return fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _case_insensitive_substring_pattern(term: str) -> str:
    """Build a ``LIKE`` pattern (``%…%``) for substring search; term is lowercased for ``lower(col) LIKE``."""

    return f"%{_escape_sql_like_metacharacters(term.lower())}%"


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Experiment)

    async def get_user_experiments(
        self,
        user: UserProtocol,
        list_options: ListOptions | None = None,
    ) -> Page[Experiment]:
        filters = [Experiment.started_by == user.id]
        return await self.list(
            *filters,
            order_by=Experiment.created_at.desc(),
            list_options=list_options,
        )

    async def get_latest_experiments(
        self,
        project_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(limit=10, offset=0),
        *,
        include_features: bool = True,
    ) -> Page[Experiment]:
        filters = [Experiment.project_id == project_id]
        return await self.list(
            *filters,
            order_by=Experiment.created_at.desc(),
            load=[] if include_features else [defer(Experiment.features)],
            list_options=list_options,
        )

    async def get_experiments_by_project(
        self,
        project_id: UUID_TYPE,
        full_load: LoadOptions = False,
        list_options: ListOptions | None = None,
        *,
        search: str | None = None,
        include_features: bool = True,
    ) -> Page[Experiment]:
        if isinstance(full_load, Sequence):
            load = [selectinload(getattr(Experiment, option)) for option in full_load]
        elif full_load:
            load = [selectinload(Experiment.project), selectinload(Experiment.metrics)]
        else:
            load = []
        if not include_features:
            load.append(defer(Experiment.features))
        filters = [Experiment.project_id == project_id]
        if search and (term := search.strip()[:200]):
            # Portable across PostgreSQL and SQLite: avoid ``instr()`` (SQLite-only in practice for PG).
            pat = _case_insensitive_substring_pattern(term)
            desc_col = func.coalesce(Experiment.description, "")
            tags_col = func.coalesce(cast(Experiment.tags, String), "[]")
            filters.append(
                or_(
                    func.lower(Experiment.name).like(pat, escape="\\"),
                    func.lower(desc_col).like(pat, escape="\\"),
                    func.lower(cast(Experiment.id, String)).like(pat, escape="\\"),
                    func.lower(tags_col).like(pat, escape="\\"),
                )
            )
        return await self.list(
            *filters,
            order_by=[Experiment.created_at.desc(), Experiment.id.desc()],
            load=load,
            list_options=list_options,
        )

    async def get_experiments_by_ids(
        self, experiment_ids: List[UUID_TYPE], *, include_features: bool = True
    ) -> List[Experiment]:
        if not experiment_ids:
            return []
        filters = [Experiment.id.in_(experiment_ids)]
        experiments = list(
            await self.advanced_alchemy_repository.list(
                *filters,
                load=[] if include_features else [defer(Experiment.features)],
            )
        )
        return experiments

    async def list_experiment_ids_for_project_by_created_at_desc(
        self, project_id: UUID_TYPE
    ) -> List[UUID_TYPE]:
        """Project experiment ids for paging UIs: newest first, stable on id."""
        stmt = (
            select(Experiment.id)
            .where(Experiment.project_id == project_id)
            .order_by(Experiment.created_at.desc(), Experiment.id.desc())
        )
        res = await self.db.execute(stmt)
        return [r[0] for r in res.all()]
