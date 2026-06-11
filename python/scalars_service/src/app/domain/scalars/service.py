import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Literal, Sequence, cast
from uuid import UUID, uuid4

from experiment_tracker_shared import utc_naive_for_clickhouse_insert, utc_now_naive
from experiment_tracker_shared.scalar_values import (
    ScalarWireValue,
    scalar_from_wire,
    scalar_to_wire,
)
from experiment_tracker_shared.datetime_utc import to_json_utc_z

from app.domain.projects.dto import (  # type: ignore
    ClickhouseTableUsageStats,
    ExperimentClickhouseUsageResponseDTO,
    ListStorageTablesResponseDTO,
    StorageTableRowDTO,
    ProjectClickhouseUsageResponseDTO,
)
from app.domain.scalars.dto import (  # type: ignore
    CompactProjectColumnsResponseDTO,
    ExperimentsScalarsPointsResultDTO,
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    LogScalarResponseDTO,
    LogScalarsResponseDTO,
    ScalarSeriesDTO,
    ScalarsPointsResultDTO,
    ScalarsSampling,
    StepTagsDTO,
)
from app.domain.utils.scalars_db_utils import (  # type: ignore
    SCALARS_DB_UTILS,
    ProjectTableColumns,
)
from app.domain.utils.scalars_select_sql import SCALARS_SELECT_SQL  # type: ignore
from app.infrastructure.cache.cache import Cache  # type: ignore

logger = logging.getLogger(__name__)


def _sampling_cache_fragment(sampling: ScalarsSampling | Literal["*"]) -> str:
    """Map a sampling mode (or invalidation wildcard) to the string embedded in cache keys.

    Args:
        sampling: Concrete ``ScalarsSampling`` value, or the literal ``"*"`` so that
            ``invalidate`` patterns match every cached entry regardless of sampling mode.

    Returns:
        The enum wire value (e.g. ``"uniform"``), or ``"*"`` when ``sampling`` is ``"*"``.
    """
    if sampling == "*":
        return "*"
    return sampling.value


def _build_scalars_cache_key(
    project_id: UUID,
    experiment_id: UUID | None,
    max_points: int | None | Literal["*"],
    return_tags: bool | Literal["*"],
    sampling: ScalarsSampling | Literal["*"],
    columns_per_query: int | Literal["*"],
    limit: int | Literal["*"],
    offset: int | Literal["*"],
) -> str:
    """Build a single-line cache key for ``get_scalars`` GET responses.

    Only **unbounded** queries (no ``start_time`` / ``end_time``) use the cache; callers must
    skip cache read/write when time bounds are set.

    Keys distinguish project, experiment scope, query knobs (``max_points``,
    ``columns_per_query``, pagination), and sampling. Passing ``"*"`` for tunable fields
    produces glob-friendly segments so ``Cache.invalidate`` can drop every variant after a log.

    Args:
        project_id: Project whose scalars table is queried.
        experiment_id: One experiment UUID for per-experiment cache entries.
        max_points: Per-metric cap passed to ClickHouse, or ``"*"`` for pattern match.
        return_tags: Whether tags were included in the response, or ``"*"``.
        sampling: Sampling enum or ``"*"``.
        columns_per_query: Parallel column batch size, or ``"*"``.
        limit: Experiment page size (or ``-1`` when omitted from per-experiment keys), or ``"*"``.
        offset: Experiment page offset (or ``-1`` when omitted from per-experiment keys), or ``"*"``.

    Returns:
        A unique string suitable for ``Cache.get`` / ``Cache.set`` / ``Cache.invalidate`` matching.
    """
    sampling_key = _sampling_cache_fragment(sampling)
    return (
        f"scalars:project:{project_id}:experiment:{experiment_id}:max_points:{max_points}:"
        f"sampling:{sampling_key}:return_tags:{return_tags}"
        f":columns_per_query:{columns_per_query}:limit:{limit}:offset:{offset}"
    )


def clean_scalar_name(name: str) -> str:
    """Clean scalar name.
    Replace spaces with underscores and remove leading and trailing spaces.
    Keep in mind that scalar names are not validated in any way.
    This method is used to clean scalar names before using them in the database.
    It is not used to validate scalar names.

    Args:
        name (str): The scalar name.

    Returns:
        str: The cleaned scalar name.
    """
    return name.strip().replace(" ", "_")


class ScalarsService:
    def __init__(self, client, cache: Cache | None = None, last_logged_service=None):
        self.client = client
        self.cache = cache
        self.last_logged_service = last_logged_service
        self.default_max_points: int = 1000

    async def log_scalar(
        self, project_id: UUID, experiment_id: UUID, request: LogScalarRequestDTO
    ):
        """Log a scalar for a given project and experiment.

        Args:
            project_id (UUID): The project ID.
            experiment_id (UUID): The experiment ID.
            request (LogScalarRequestDTO): The request containing the scalar and tags.

        Returns:
            LogScalarResponseDTO: The response containing the status and warnings.
        """
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        await self._ensure_scalars_table(project_id=project_id)
        # We must invalidate cache because we are logging a scalar for a given experiment.
        if self.cache is not None:
            await self._invalidate_cache(
                project_id=project_id, experiment_id=experiment_id
            )
        # Filter out conflicting scalars and return warnings if any.
        filtered_scalars, warnings = self._filter_conflicting_scalars(
            scalars=request.scalars
        )
        if not filtered_scalars:
            return LogScalarResponseDTO(status="logged", warnings=warnings or None)

        # Get or create scalar mapping (because them stored per step and single column per scalar).
        # Table columns can't be random strings, so we need to map them to internal names.

        mapping = await self._get_or_create_scalar_mapping(project_id=project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping=mapping, scalar_names=filtered_scalars.keys()
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id=project_id, mapping=mapping)
            # Ensure that the table and columns exist. If not, create them. If columns are missing, add them.
        # Because clickhouse doesn't support transactions, we need to ensure that the table and columns exist before logging the scalar.
        await self._ensure_scalars_columns(
            table_name=table_name, scalar_columns=list(mapped_columns.values())
        )

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        logged_at = utc_now_naive()
        row = [
            utc_naive_for_clickhouse_insert(logged_at),
            experiment_id,
            request.step,
            request.tags or [],
        ] + [
            self._storage_scalar_value(filtered_scalars[name])
            for name in mapped_columns.keys()
        ]
        await self.client.insert(table=table_name, data=[row], column_names=columns)
        if self.last_logged_service:
            await self.last_logged_service.touch(
                project_id=project_id,
                experiment_id=experiment_id,
                last_modified=logged_at,
            )
        return LogScalarResponseDTO(status="logged", warnings=warnings or None)

    async def log_scalars(
        self, project_id: UUID, experiment_id: UUID, request: LogScalarsRequestDTO
    ):
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        await self._ensure_scalars_table(project_id=project_id)
        if self.cache is not None:
            await self._invalidate_cache(
                project_id=project_id, experiment_id=experiment_id
            )
        if not request.scalars:
            return LogScalarsResponseDTO(status="logged")

        warnings: list[str] = []
        filtered_items: list[LogScalarRequestDTO] = []
        for item in request.scalars:
            filtered_scalars, item_warnings = self._filter_conflicting_scalars(
                scalars=item.scalars
            )
            warnings.extend(item_warnings)
            if not filtered_scalars:
                continue
            filtered_items.append(
                LogScalarRequestDTO(
                    scalars=filtered_scalars,
                    step=item.step,
                    tags=item.tags,
                )
            )

        if not filtered_items:
            return LogScalarsResponseDTO(status="logged", warnings=warnings or None)

        all_scalar_names = {name for item in filtered_items for name in item.scalars}
        mapping = await self._get_or_create_scalar_mapping(project_id=project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping=mapping, scalar_names=all_scalar_names
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id=project_id, mapping=mapping)
        # Because clickhouse doesn't support transactions, we need to ensure that the table and columns exist before logging the scalar.
        await self._ensure_scalars_columns(
            table_name=table_name, scalar_columns=list(mapped_columns.values())
        )

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        rows = []
        last_modified = utc_now_naive()
        wire_ts = utc_naive_for_clickhouse_insert(last_modified)
        for item in filtered_items:
            row = [
                wire_ts,
                experiment_id,
                item.step,
                # Arrays can't be nullable in clickhouse, so we use empty list if tags are None.
                item.tags or [],
            ] + [
                self._storage_scalar_value(item.scalars.get(name, None))
                for name in mapped_columns.keys()
            ]
            rows.append(row)
        if rows:
            await self.client.insert(table=table_name, data=rows, column_names=columns)
            if self.last_logged_service:
                await self.last_logged_service.touch(
                    project_id=project_id,
                    experiment_id=experiment_id,
                    last_modified=last_modified,
                )
        return LogScalarsResponseDTO(status="logged", warnings=warnings or None)

    # --- get_scalars helpers (keep orchestration readable) ---

    @staticmethod
    def _normalize_experiment_id_filter(
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None,
    ) -> tuple[list[UUID] | None, bool]:
        """
        Split API input into an explicit id list vs "all experiments in project".

        Args:
            experiment_id: Experiment UUID or list of UUIDs, or ``None`` for project-wide listing.

        Returns:
            A tuple containing:
            - A list of experiment UUIDs, or ``None`` for project-wide listing.
            - A boolean indicating whether the listing is project-wide (every experiment in the project).
        """
        if experiment_id is None:
            return None, True
        if isinstance(experiment_id, UUID):
            return [experiment_id], False
        return list(experiment_id), False

    @staticmethod
    def _explicit_experiment_page_slice(
        requested_ids: list[UUID], limit: int, offset: int
    ) -> tuple[int, list[UUID]]:
        """Apply limit/offset to the caller-supplied experiment id list."""
        total = len(requested_ids)
        return total, requested_ids[offset : offset + limit]

    async def _clickhouse_distinct_experiment_page(
        self,
        table_name: str,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[UUID]]:
        """Count distinct experiments, then return one page of ids (sorted, stable order)."""
        count_sql = SCALARS_DB_UTILS.build_count_distinct_experiments_statement(
            table_name=table_name, start_time=start_time, end_time=end_time
        )
        count_res = await self.client.query(count_sql)
        total = int(count_res.result_rows[0][0])
        page_sql = SCALARS_DB_UTILS.build_select_experiment_id_page_statement(
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        page_res = await self.client.query(page_sql)
        page_ids = [cast(UUID, row[0]) for row in page_res.result_rows]
        return total, page_ids

    async def _get_scalars_try_cache(
        self,
        project_id: UUID,
        page_ids: list[UUID],
        total_experiments: int,
        max_points: int,
        return_tags: bool,
        start_time: datetime | None,
        end_time: datetime | None,
        sampling: ScalarsSampling,
        columns_per_query: int,
        limit: int,
        offset: int,
    ) -> tuple[
        ScalarsPointsResultDTO | None, dict[UUID, ExperimentsScalarsPointsResultDTO]
    ]:
        """Return a fully cached response, or partial per-experiment hits for the current page."""
        if self.cache is None:
            return None, {}
        if start_time is not None or end_time is not None:
            return None, {}

        cached_by_exp: dict[UUID, ExperimentsScalarsPointsResultDTO] = {}
        for exp_id in page_ids:
            ck = _build_scalars_cache_key(
                project_id=project_id,
                experiment_id=exp_id,
                max_points=max_points,
                return_tags=return_tags,
                sampling=sampling,
                columns_per_query=columns_per_query,
                limit=-1,
                offset=-1,
            )
            row = await self.cache.get(key=ck)
            if row is not None:
                cached_by_exp[exp_id] = row

        if len(cached_by_exp) != len(page_ids):
            return None, cached_by_exp

        ordered = [cached_by_exp[eid] for eid in page_ids]
        return (
            ScalarsPointsResultDTO(
                data=ordered,
                has_next=offset + len(page_ids) < total_experiments,
                size=len(ordered),
                total=total_experiments,
            ),
            {},
        )

    async def _load_sampled_columns_for_experiments(
        self,
        table_name: str,
        experiment_ids: list[UUID],
        project_id: UUID,
        scalar_columns: list[str],
        start_time: datetime | None,
        end_time: datetime | None,
        max_points: int,
        columns_per_query: int,
        return_tags: bool,
    ) -> tuple[
        defaultdict[UUID, dict[str, ScalarSeriesDTO]],
        dict[tuple[UUID, int], StepTagsDTO],
    ]:
        """Run per-column ClickHouse queries (batched) and merge into in-memory structures."""
        mapping = await self._get_or_create_scalar_mapping(project_id)
        column_to_scalar_name = {column: scalar for scalar, column in mapping.items()}

        result_scalars: defaultdict[UUID, dict[str, ScalarSeriesDTO]] = defaultdict(
            dict
        )
        tag_by_exp_step: dict[tuple[UUID, int], StepTagsDTO] = {}

        for i in range(0, len(scalar_columns), columns_per_query):
            batch = scalar_columns[i : i + columns_per_query]
            chunks = await asyncio.gather(
                *[
                    self._fetch_uniform_sampled_column(
                        table_name=table_name,
                        internal_col=col,
                        experiment_ids=experiment_ids,
                        start_time=start_time,
                        end_time=end_time,
                        max_points=max_points,
                    )
                    for col in batch
                ]
            )
            for internal_col, col_names, rows in chunks:
                public_name = column_to_scalar_name.get(internal_col, internal_col)
                self._merge_uniform_column_rows(
                    column_names=col_names,
                    rows=rows,
                    internal_col=internal_col,
                    public_name=public_name,
                    result_scalars=result_scalars,
                    tag_by_exp_step=tag_by_exp_step,
                    return_tags=return_tags,
                )
        return result_scalars, tag_by_exp_step

    @staticmethod
    def _assemble_get_scalars_page(
        page_ids: list[UUID],
        cached_by_exp: dict[UUID, ExperimentsScalarsPointsResultDTO],
        result_scalars: defaultdict[UUID, dict[str, ScalarSeriesDTO]],
        tag_by_exp_step: dict[tuple[UUID, int], StepTagsDTO],
        return_tags: bool,
    ) -> list[ExperimentsScalarsPointsResultDTO]:
        """Build one DTO per experiment on the page (cache hit or freshly merged series)."""
        merged: list[ExperimentsScalarsPointsResultDTO] = []
        for eid in page_ids:
            if eid in cached_by_exp:
                merged.append(cached_by_exp[eid])
                continue
            scalars = result_scalars.get(eid, {})
            tags_list: list[StepTagsDTO] | None = None
            if return_tags:
                tags_list = sorted(
                    (
                        dto
                        for (exp_s, _s), dto in tag_by_exp_step.items()
                        if exp_s == eid
                    ),
                    key=lambda d: d.step,
                )
                if not tags_list:
                    tags_list = None
            merged.append(
                ExperimentsScalarsPointsResultDTO(
                    experiment_id=eid,
                    scalars=scalars,
                    tags=tags_list,
                )
            )
        return merged

    async def _store_get_scalars_cache(
        self,
        project_id: UUID,
        merged: list[ExperimentsScalarsPointsResultDTO],
        skip_experiment_ids: frozenset[UUID],
        max_points: int,
        return_tags: bool,
        start_time: datetime | None,
        end_time: datetime | None,
        sampling: ScalarsSampling,
        columns_per_query: int,
    ) -> None:
        """Persist per-experiment payloads for full-range (unbounded) queries only."""
        if self.cache is None:
            return
        if start_time is not None or end_time is not None:
            return
        for item in merged:
            if item.experiment_id in skip_experiment_ids:
                continue
            ck = _build_scalars_cache_key(
                project_id=project_id,
                experiment_id=item.experiment_id,
                max_points=max_points,
                return_tags=return_tags,
                sampling=sampling,
                columns_per_query=columns_per_query,
                limit=-1,
                offset=-1,
            )
            await self.cache.set(key=ck, value=item)

    async def get_scalars(
        self,
        project_id: UUID,
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None = None,
        limit: int = 100,
        offset: int = 0,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        sampling: ScalarsSampling = ScalarsSampling.UNIFORM,
        columns_per_query: int = 1,
    ):
        """Get scalars for a given project and experiment.

        Experiments are resolved and paginated first (``limit`` / ``offset`` on the
        experiment id list). Scalar values are loaded **per storage column** with
        ClickHouse-side ``IS NOT NULL`` filtering and uniform subsampling per
        experiment and column (see ``build_select_uniform_sampled_column``).

        A future ``density`` parameter may group scalar columns for batched fetches;
        today ``columns_per_query`` only controls parallel fan-out (default ``1``).

        Args:
            project_id (UUID): The project ID.
            experiment_id (UUID | list[UUID] | tuple[UUID, ...] | None): Filter; ``None`` lists all experiments in the project (paginated).
            max_points (int | None): Max **non-null** points per experiment **per metric** after uniform sampling in SQL.
            columns_per_query (int): Number of per-column queries to run concurrently (>= 1).

        Returns:
            ScalarsPointsResultDTO: The scalars points result.
        """
        if max_points is None:
            max_points = self.default_max_points
        if columns_per_query < 1:
            raise ValueError("columns_per_query must be >= 1")
        if start_time is not None and end_time is not None and start_time > end_time:
            raise ValueError("start_time must be less than or equal to end_time")

        requested_ids, browse_all = self._normalize_experiment_id_filter(experiment_id)

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        if not await self._table_exists(table_name=table_name):
            if browse_all:
                return ScalarsPointsResultDTO(data=[], has_next=False, size=0, total=0)
            assert requested_ids is not None
            total_experiments, page_ids = self._explicit_experiment_page_slice(
                requested_ids=requested_ids, limit=limit, offset=offset
            )
            return ScalarsPointsResultDTO(
                data=[],
                has_next=False,
                size=0,
                total=total_experiments,
            )

        if browse_all:
            total_experiments, page_ids = (
                await self._clickhouse_distinct_experiment_page(
                    table_name=table_name,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    offset=offset,
                )
            )
        else:
            assert requested_ids is not None
            total_experiments, page_ids = self._explicit_experiment_page_slice(
                requested_ids=requested_ids, limit=limit, offset=offset
            )

        if start_time is not None or end_time is not None:
            logger.debug(
                "get_scalars bounded query project_id=%s page_experiment_ids=%s start_time=%s end_time=%s",
                project_id,
                [str(eid) for eid in page_ids],
                to_json_utc_z(start_time) if start_time else None,
                to_json_utc_z(end_time) if end_time else None,
            )

        cached_full, cached_by_exp = await self._get_scalars_try_cache(
            project_id=project_id,
            page_ids=page_ids,
            total_experiments=total_experiments,
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
            sampling=sampling,
            columns_per_query=columns_per_query,
            limit=limit,
            offset=offset,
        )
        if cached_full is not None:
            return cached_full

        # Load ClickHouse only for experiments on this page that were not cache hits.
        ids_to_fetch = [eid for eid in page_ids if eid not in cached_by_exp]

        scalar_columns = await self._get_scalar_columns(table_name=table_name)
        result_scalars: defaultdict[UUID, dict[str, ScalarSeriesDTO]] = defaultdict(
            dict
        )
        tag_by_exp_step: dict[tuple[UUID, int], StepTagsDTO] = {}
        if ids_to_fetch and scalar_columns:
            result_scalars, tag_by_exp_step = (
                await self._load_sampled_columns_for_experiments(
                    table_name=table_name,
                    experiment_ids=ids_to_fetch,
                    project_id=project_id,
                    scalar_columns=scalar_columns,
                    start_time=start_time,
                    end_time=end_time,
                    max_points=max_points,
                    columns_per_query=columns_per_query,
                    return_tags=return_tags,
                )
            )

        merged = self._assemble_get_scalars_page(
            page_ids=page_ids,
            cached_by_exp=cached_by_exp,
            result_scalars=result_scalars,
            tag_by_exp_step=tag_by_exp_step,
            return_tags=return_tags,
        )
        response = ScalarsPointsResultDTO(
            data=merged,
            has_next=offset + len(page_ids) < total_experiments,
            size=len(merged),
            total=total_experiments,
        )

        await self._store_get_scalars_cache(
            project_id=project_id,
            merged=merged,
            skip_experiment_ids=frozenset(cached_by_exp),
            max_points=max_points,
            return_tags=return_tags,
            start_time=start_time,
            end_time=end_time,
            sampling=sampling,
            columns_per_query=columns_per_query,
        )
        return response

    async def compact_project_columns(
        self, project_id: UUID
    ) -> CompactProjectColumnsResponseDTO:
        """Drop empty metric columns from the project scalars table and trim the mapping.

        For each mapped scalar column, if no row has a non-null value, runs
        ``ALTER TABLE … DROP COLUMN`` on that storage column, then saves the mapping
        with those scalar names removed. Base columns (timestamp, experiment, step, tags)
        are unchanged.
        """

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        if not await self._table_exists(table_name):
            return CompactProjectColumnsResponseDTO(dropped_columns=[])
        mapping = await self._get_or_create_scalar_mapping(project_id)
        dropped: list[str] = []
        kept_mapping = dict(mapping)
        for scalar_name, column_name in list(mapping.items()):
            safe_column = SCALARS_DB_UTILS.validate_scalar_storage_column_name(
                column_name
            )
            result = await self.client.query(
                SCALARS_SELECT_SQL.count_non_null_column(table_name, safe_column)
            )
            count = int(result.result_rows[0][0]) if result.result_rows else 0
            if count == 0:
                await self.client.command(
                    SCALARS_DB_UTILS.build_alter_table_drop_column_if_exists_statement(
                        table_name, safe_column
                    )
                )
                kept_mapping.pop(scalar_name, None)
                dropped.append(safe_column)
        if dropped:
            await self._save_scalar_mapping(project_id=project_id, mapping=kept_mapping)
        return CompactProjectColumnsResponseDTO(dropped_columns=dropped)

    async def invalidate_cache_for_experiment(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        """Clear ``get_scalars`` cache after writes that affect this experiment (orchestration hook)."""
        await self._invalidate_cache(project_id=project_id, experiment_id=experiment_id)

    async def create_clickhouse_table(self, project_id: UUID) -> str:
        """Run DDL for this project's scalars table (base columns only)."""
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        ddl = SCALARS_DB_UTILS.build_create_scalars_table_statement(
            table_name=table_name
        )
        await self.client.command(ddl)
        return table_name

    async def get_scalars_table_existence(self, project_id: UUID) -> tuple[str, bool]:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        exists = await self._table_exists(table_name=table_name)
        return table_name, exists

    async def list_experiment_ids_for_project(self, project_id: UUID) -> list[dict]:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        query = SCALARS_DB_UTILS.build_experiments_ids_statement(table_name)
        result = await self.client.query(query)
        return [{"experiment_id": row[0]} for row in result.result_rows]

    async def delete_scalar_mapping_for_project(self, project_id: UUID) -> None:
        await self.client.command(
            SCALARS_DB_UTILS.build_delete_mapping_statement(project_id)
        )

    async def drop_clickhouse_table(self, project_id: UUID) -> str:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )
        return table_name

    async def delete_experiment_rows_if_table_exists(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        if not await self._table_exists(table_name=table_name):
            return
        await self.client.command(
            SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
                table_name=table_name,
                experiment_id=experiment_id,
                experiment_id_column=ProjectTableColumns.EXPERIMENT_ID.value,
            )
        )

    async def get_clickhouse_table_usage_stats(
        self, project_id: UUID
    ) -> ClickhouseTableUsageStats:
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        if not await self._table_exists(table_name=table_name):
            return ClickhouseTableUsageStats(
                table=table_name,
                exists=False,
                rows=0,
                columns=0,
                bytes=0,
            )
        rows_result = await self.client.query(
            SCALARS_SELECT_SQL.count_all_rows(table_name)
        )
        rows = int(rows_result.result_rows[0][0]) if rows_result.result_rows else 0
        columns_result = await self.client.query(
            SCALARS_DB_UTILS.build_describe_table_statement(table_name)
        )
        columns = len(columns_result.result_rows)
        bytes_result = await self.client.query(
            SCALARS_SELECT_SQL.sum_bytes_on_disk_active_parts(
                SCALARS_DB_UTILS.escape_sql_literal(table_name)
            )
        )
        bytes_on_disk = (
            int(bytes_result.result_rows[0][0]) if bytes_result.result_rows else 0
        )
        return ClickhouseTableUsageStats(
            table=table_name,
            exists=True,
            rows=rows,
            columns=columns,
            bytes=bytes_on_disk,
        )

    async def get_experiment_usage_estimate(
        self,
        project_id: UUID,
        experiment_id: UUID,
        project_table_stats: (
            Sequence[ClickhouseTableUsageStats] | ProjectClickhouseUsageResponseDTO
        ),
    ) -> ExperimentClickhouseUsageResponseDTO:
        if isinstance(project_table_stats, ProjectClickhouseUsageResponseDTO):
            table_rows = [
                ClickhouseTableUsageStats(
                    table=t.table,
                    exists=t.exists,
                    rows=t.rows,
                    columns=t.columns,
                    bytes=t.bytes,
                )
                for t in project_table_stats.tables
            ]
        else:
            table_rows = list(project_table_stats)
        scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not await self._table_exists(table_name=scalars_table):
            return ExperimentClickhouseUsageResponseDTO(
                project_id=project_id,
                experiment_id=experiment_id,
                rows=0,
                bytes=0,
            )
        total_rows_result = await self.client.query(
            SCALARS_SELECT_SQL.count_all_rows(scalars_table)
        )
        exp_rows_result = await self.client.query(
            SCALARS_SELECT_SQL.count_rows_for_experiment(
                scalars_table,
                ProjectTableColumns.EXPERIMENT_ID.value,
                str(experiment_id),
            )
        )
        total_rows = (
            int(total_rows_result.result_rows[0][0])
            if total_rows_result.result_rows
            else 0
        )
        exp_rows = (
            int(exp_rows_result.result_rows[0][0]) if exp_rows_result.result_rows else 0
        )
        table_bytes = next(
            (row.bytes for row in table_rows if row.table == scalars_table),
            0,
        )
        estimated_bytes = (
            int(table_bytes * (exp_rows / total_rows)) if total_rows else 0
        )
        return ExperimentClickhouseUsageResponseDTO(
            project_id=project_id,
            experiment_id=experiment_id,
            rows=exp_rows,
            bytes=estimated_bytes,
        )

    async def list_admin_storage_tables(
        self,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ListStorageTablesResponseDTO:
        extra = ""
        if q and q.strip():
            needle = re.sub(r"[^a-zA-Z0-9_.\-]", "", q.strip())[:200]
            if needle:
                safe = needle.replace("'", "''")
                extra = f" AND positionCaseInsensitive(name, '{safe}') > 0"
        lim = max(1, min(int(limit), 200))
        off = max(0, int(offset))
        count_result = await self.client.query(
            SCALARS_SELECT_SQL.list_tables_count(extra)
        )
        total = int(count_result.result_rows[0][0]) if count_result.result_rows else 0
        result = await self.client.query(
            SCALARS_SELECT_SQL.list_tables_page(
                extra_predicate=extra, limit=lim, offset=off
            )
        )
        return ListStorageTablesResponseDTO(
            tables=[
                StorageTableRowDTO(
                    name=row[0],
                    rows=int(row[1] or 0),
                    bytes=int(row[2] or 0),
                )
                for row in result.result_rows
            ],
            total=total,
            limit=lim,
            offset=off,
        )

    async def drop_managed_table_by_name(self, table_name: str) -> None:
        if not table_name.startswith("scalars_"):
            raise ValueError("Only scalar-service managed tables can be dropped")
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Invalid table name")
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )

    async def _fetch_uniform_sampled_column(
        self,
        table_name: str,
        internal_col: str,
        experiment_ids: list[UUID],
        start_time: datetime | None,
        end_time: datetime | None,
        max_points: int,
    ) -> tuple[str, Sequence[str], list[Sequence[object]]]:
        """Execute one sampled column query against ClickHouse.

        SQL keeps only rows where the metric is non-null, then applies a uniform subsample
        of at most ``max_points`` rows **per experiment** ordered by step (see
        ``build_select_uniform_sampled_column``).

        Args:
            table_name: ClickHouse scalars table name for this project.
            internal_col: Storage column (e.g. ``c_<hex>``) for this metric.
            experiment_ids: Experiments to include (non-empty); already paginated by the caller.
            start_time: Optional lower timestamp bound on ``__timestamp__``.
            end_time: Optional upper timestamp bound on ``__timestamp__``.
            max_points: Maximum retained non-null points per experiment for this column.

        Returns:
            A triple ``(internal_col, column_names, result_rows)`` where ``column_names`` /
            ``result_rows`` come from the driver query result and are consumed by
            ``_merge_uniform_column_rows``.
        """
        sql = SCALARS_DB_UTILS.build_select_uniform_sampled_column(
            table_name=table_name,
            column_name=internal_col,
            experiment_ids=experiment_ids,
            start_time=start_time,
            end_time=end_time,
            max_points=max_points,
        )
        res = await self.client.query(sql)
        return internal_col, res.column_names, res.result_rows

    def _merge_uniform_column_rows(
        self,
        column_names: Sequence[str],
        rows: list[Sequence[object]],
        internal_col: str,
        public_name: str,
        result_scalars: defaultdict[UUID, dict[str, ScalarSeriesDTO]],
        tag_by_exp_step: dict[tuple[UUID, int], StepTagsDTO],
        return_tags: bool,
    ) -> None:
        """Fold one column query result into the in-memory aggregates used to build the HTTP DTO.

        For each row, appends ``(step, value)`` to the series named ``public_name`` under the row's
        experiment. Skips null values defensively. When ``return_tags`` is true and the row has
        tags, updates ``tag_by_exp_step`` so a single ``StepTagsDTO`` per ``(experiment_id, step)``
        accumulates every metric name that contributed at that step.

        Args:
            column_names: Names from the ClickHouse client (order matches each row tuple).
            rows: Raw result rows for this column query.
            internal_col: Storage column name present in ``column_names`` and each row.
            public_name: User-facing metric name (from the scalar mapping).
            result_scalars: Mutable map ``experiment_id -> {metric_name -> ScalarSeriesDTO}``.
            tag_by_exp_step: Mutable map ``(experiment_id, step) -> StepTagsDTO`` for tag merging.
            return_tags: When false, tag columns are ignored.

        Returns:
            None; mutates ``result_scalars`` and ``tag_by_exp_step`` in place.
        """
        col_index = {name: idx for idx, name in enumerate(column_names)}
        exp_k = ProjectTableColumns.EXPERIMENT_ID.value
        step_k = ProjectTableColumns.STEP.value
        tags_k = ProjectTableColumns.TAGS.value
        for row in rows:
            experiment_id = cast(UUID, row[col_index[exp_k]])
            step = cast(int, row[col_index[step_k]])
            value = row[col_index[internal_col]]
            if value is None:
                continue
            series = result_scalars[experiment_id].setdefault(
                public_name,
                ScalarSeriesDTO(x=[], y=[]),
            )
            series.x.append(step)
            series.y.append(scalar_to_wire(cast(float, value)))
            if return_tags:
                tags = cast(list[str], row[col_index[tags_k]] or [])
                if tags:
                    key = (experiment_id, step)
                    existing = tag_by_exp_step.get(key)
                    if existing is None:
                        tag_by_exp_step[key] = StepTagsDTO(
                            step=step,
                            scalar_names=[public_name],
                            tags=tags,
                        )
                    elif public_name not in existing.scalar_names:
                        tag_by_exp_step[key] = existing.model_copy(
                            update={
                                "scalar_names": sorted(
                                    [*existing.scalar_names, public_name]
                                )
                            },
                        )

    async def _ensure_scalars_table(self, project_id: UUID) -> None:
        """Ensure the scalars table exists. Create it with base columns only if it does not."""
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id=project_id)
        if not await self._table_exists(table_name=table_name):
            ddl = SCALARS_DB_UTILS.build_create_scalars_table_statement(
                table_name=table_name
            )
            await self.client.command(ddl)

    async def _table_exists(self, table_name: str) -> bool:
        """Check if the table exists.

        Args:
            table_name (str): The table name.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        # Query returns count of rows > 0 if table exists.
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name=table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])

    async def _get_table_columns(self, table_name: str) -> list[str]:
        query = SCALARS_DB_UTILS.build_describe_table_statement(table_name=table_name)
        result = await self.client.query(query)
        return [row[0] for row in result.result_rows]

    async def _get_scalar_columns(self, table_name: str) -> list[str]:
        columns = await self._get_table_columns(table_name=table_name)
        base_columns = set(SCALARS_DB_UTILS.get_base_columns())
        return [col for col in columns if col not in base_columns]

    async def _ensure_scalars_columns(
        self, table_name: str, scalar_columns: Sequence[str]
    ) -> None:
        """Ensure that the table and columns exist. If not, create them. If columns are missing, add them.

        Args:
            table_name (str): The table name.
            scalar_columns (Sequence[str]): The scalar columns.

        Returns:
            None: The function does not return anything.
        """
        existing_columns = set(await self._get_table_columns(table_name=table_name))
        missing = [col for col in scalar_columns if col not in existing_columns]
        if missing:
            ddl = SCALARS_DB_UTILS.build_alter_table_add_columns_statement(
                table_name=table_name, scalar_columns=missing
            )
            await self.client.command(ddl)

    @staticmethod
    def _storage_scalar_value(value: ScalarWireValue | None) -> float | None:
        if value is None:
            return None
        return scalar_from_wire(value)

    def _filter_conflicting_scalars(
        self, scalars: dict[str, ScalarWireValue]
    ) -> tuple[dict[str, ScalarWireValue], list[str]]:
        """Filter out conflicting scalars and return warnings if any.
        Keep in mind that scalars are not validated in any way.
        This method is used to filter out scalars that are not valid (uses internal names for scalars).

        Args:
            scalars (dict[str, ScalarWireValue]): The scalars to filter.

        Returns:
            tuple[dict[str, ScalarWireValue], list[str]]: The filtered scalars and warnings.
        """
        filtered: dict[str, ScalarWireValue] = {}
        warnings: list[str] = []
        for name, value in scalars.items():
            cleaned_name = clean_scalar_name(name)
            if not cleaned_name or not cleaned_name.strip():
                warnings.append("Scalar name is empty and was skipped.")
                continue
            if cleaned_name in filtered:
                warnings.append(
                    f"Scalar name {cleaned_name} is already in use and was skipped."
                )
                continue
            filtered[cleaned_name] = value
        return filtered, warnings

    async def _load_scalar_mapping(self, project_id: UUID) -> dict[str, str] | None:
        """Load scalar mapping from the database.

        Args:
            project_id (UUID): The project ID.

        Returns:
            dict[str, str] | None: The scalar mapping. Keys are scalar names, values are internal column names.
            None if mapping is not found or is empty.
        """
        # Build statement to select the mapping for a given project ID.
        query = SCALARS_DB_UTILS.build_select_mapping_statement(project_id=project_id)
        result = await self.client.query(query)
        # If no mapping is found, return None.
        if not result.result_rows:
            return None
        mapping_value = result.result_rows[0][0]
        # If mapping is empty, return empty dictionary.
        if not mapping_value:
            return {}
        # If mapping is not a dictionary, raise an error.
        if not isinstance(mapping_value, dict):
            raise ValueError("Mapping value is not a dictionary")
        return {str(k): str(v) for k, v in mapping_value.items()}

    async def _save_scalar_mapping(
        self, project_id: UUID, mapping: dict[str, str]
    ) -> None:
        """Save scalar mapping to the database.

        Args:
            project_id (UUID): The project ID.
            mapping (dict[str, str]): The scalar mapping.

        Returns:
            None: The function does not return anything.
        """
        payload = {str(k): str(v) for k, v in mapping.items()}
        await self.client.insert(
            table=SCALARS_DB_UTILS.get_mapping_table_name(),
            data=[
                [
                    project_id,
                    payload,
                    utc_naive_for_clickhouse_insert(utc_now_naive()),
                ]
            ],
            column_names=["project_id", "mapping", "updated_at"],
        )

    async def _get_or_create_scalar_mapping(self, project_id: UUID) -> dict[str, str]:
        """Get or create scalar mapping.

        Mapping is used to map scalar names to internal column names.
        It is stored in the database and used to resolve scalar names to internal column names.
        This is needed because table columns can't be random strings, so we need to map them to internal names.

        Args:
            project_id (UUID): The project ID.

        Returns:
            dict[str, str]: The scalar mapping. Keys are scalar names, values are internal column names.
        """
        mapping = await self._load_scalar_mapping(project_id=project_id)
        if mapping is None:
            mapping = {}
        return mapping

    def _resolve_scalar_columns(
        self, mapping: dict[str, str], scalar_names: Sequence[str]
    ) -> tuple[dict[str, str], bool]:
        """Resolve scalar columns.

        Args:
            mapping (dict[str, str]): The scalar mapping.
            scalar_names (Sequence[str]): The scalar names.

        Returns:
            tuple[dict[str, str], bool]: The resolved scalar columns and if mapping was updated.
        """
        updated = False
        existing_columns = set(mapping.values())
        resolved: dict[str, str] = {}
        for name in scalar_names:
            if name in mapping:
                resolved[name] = mapping[name]
                continue
            mapping[name] = self._generate_scalar_column_name(
                existing_columns=existing_columns
            )
            existing_columns.add(mapping[name])
            resolved[name] = mapping[name]
            updated = True
        return resolved, updated

    def _generate_scalar_column_name(self, existing_columns: set[str]) -> str:
        """Generate a unique scalar column name."""
        while True:
            candidate = f"c_{uuid4().hex}"
            if candidate not in existing_columns:
                return candidate

    async def _invalidate_cache(self, project_id: UUID, experiment_id: UUID) -> None:
        """Remove cached ``get_scalars`` entries for this experiment (per-experiment keys only)."""
        if self.cache is None:
            return
        cache_key_pattern = _build_scalars_cache_key(
            project_id=project_id,
            experiment_id=experiment_id,
            max_points="*",
            return_tags="*",
            sampling="*",
            columns_per_query="*",
            limit="*",
            offset="*",
        )
        await self.cache.invalidate(pattern=cache_key_pattern)
