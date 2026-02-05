from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal, Sequence

from app.domain.scalars.dto import (
    ExperimentsScalarsPointsResultDTO,
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    LogScalarResponseDTO,
    LogScalarsResponseDTO,
    ScalarsPointsResultDTO,
    StepTagsDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS, ProjectTableColumns
from app.infrastructure.cache.cache import Cache


def _get_now_datetime() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_scalars_cache_key(
    project_id: str,
    experiment_id: str | None,
    max_points: int | None | Literal["*"],
    return_tags: bool | Literal["*"],
) -> str:
    return f"scalars:project:{project_id}:experiment:{experiment_id}:max_points:{max_points}:return_tags:{return_tags}"


# TODO: Add cache invalidation when scalar is logged (for case when we get all elements from cache (when experiment_id is None)))
class ScalarsService:
    def __init__(self, client, cache: Cache | None = None):
        self.client = client
        self.cache = cache
        self.default_max_points: int = 1000

    async def log_scalar(
        self, project_id: str, experiment_id: str, request: LogScalarRequestDTO
    ):
        if self.cache is not None:
            await self._invalidate_cache(project_id, experiment_id)

        if not request.scalars:
            return LogScalarResponseDTO(status="logged")

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        scalar_names = self._validate_scalar_names(list(request.scalars.keys()))
        await self._ensure_table_and_columns(table_name, scalar_names)

        columns = (
            SCALARS_DB_UTILS.get_base_columns()
            + list(scalar_names)
        )
        row = [
            _get_now_datetime(),
            experiment_id,
            request.step,
            request.tags or [],
        ] + [request.scalars[name] for name in scalar_names]
        await self.client.insert(table_name, [row], column_names=columns)
        return LogScalarResponseDTO(status="logged")

    async def log_scalars(
        self, project_id: str, experiment_id: str, request: LogScalarsRequestDTO
    ):
        if self.cache is not None:
            await self._invalidate_cache(project_id, experiment_id)

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not request.scalars:
            return LogScalarsResponseDTO(status="logged")

        all_scalar_names = self._validate_scalar_names(
            sorted({name for item in request.scalars for name in item.scalars})
        )
        await self._ensure_table_and_columns(table_name, all_scalar_names)

        columns = SCALARS_DB_UTILS.get_base_columns() + list(all_scalar_names)
        rows = []
        for item in request.scalars:
            row = [
                _get_now_datetime(),
                experiment_id,
                item.step,
                item.tags or [],
            ] + [item.scalars.get(name) for name in all_scalar_names]
            rows.append(row)
        if rows:
            await self.client.insert(table_name, rows, column_names=columns)
        return LogScalarsResponseDTO(status="logged")

    async def get_scalars(
        self,
        project_id: str,
        experiment_id: str | list[str] | tuple[str, ...] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
    ):
        if max_points is None:
            max_points = self.default_max_points

        if isinstance(experiment_id, str):
            experiment_id = [experiment_id]

        # We already defined result as list, because we will append to it in the loop
        result = []
        excluded_experiment_ids: list[str] = []
        # Try to get from cache
        if self.cache is not None:
            if experiment_id is None:
                # Get all scalars from cache
                cache_key = _build_scalars_cache_key(
                    project_id, None, max_points, return_tags
                )
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            else:
                # Get scalars from cache for each experiment id
                for exp_id in experiment_id:
                    query_cache_key = _build_scalars_cache_key(
                        project_id, exp_id, max_points, return_tags
                    )
                    cached_result = await self.cache.get(query_cache_key)
                    if cached_result is not None:
                        excluded_experiment_ids.append(exp_id)
                        result.append(cached_result)
                if len(result) == len(experiment_id):
                    return ScalarsPointsResultDTO(data=result)
                # Remove excluded experiment ids from experiment_id
                for exp_id in excluded_experiment_ids:
                    experiment_id.remove(exp_id)  # type: ignore

        # If not in cache, get from database
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if experiment_id is not None:
            if len(excluded_experiment_ids) > 0:
                experiment_id = [
                    exp_id
                    for exp_id in experiment_id
                    if exp_id not in excluded_experiment_ids
                ]

        if not await self._table_exists(table_name):
            return ScalarsPointsResultDTO(data=result)

        scalar_columns = await self._get_scalar_columns(table_name)
        select_statement = SCALARS_DB_UTILS.build_select_statement(
            table_name,
            scalar_columns=scalar_columns,
            experiment_ids=experiment_id,
        )
        query_result = await self.client.query(select_statement)
        result_scalars, result_tags = self._split_scalars_by_experiment_id(
            query_result.column_names,
            query_result.result_rows,
            scalar_columns,
            return_tags,
        )

        for exp_id, scalars in result_scalars.items():
            tags = None
            if return_tags:
                tags = result_tags.get(exp_id, [])
            result_item = ExperimentsScalarsPointsResultDTO(
                experiment_id=exp_id,
                scalars=scalars,
                tags=tags,
            )
            result.append(result_item)

        response = ScalarsPointsResultDTO(data=result)

        # Cache results
        if self.cache is not None:
            # Set cache for each experiment id
            for result_item in result:
                if result_item.experiment_id in excluded_experiment_ids:
                    continue
                cache_key = _build_scalars_cache_key(
                    project_id, result_item.experiment_id, max_points, return_tags
                )
                await self.cache.set(cache_key, result_item)
            # Set cache for all scalars (no experiment id)
            if experiment_id is None:
                cache_key = _build_scalars_cache_key(
                    project_id, None, max_points, return_tags
                )
                await self.cache.set(cache_key, response)
        return response

    def _split_scalars_by_experiment_id(
        self,
        column_names: Sequence[str],
        rows: list[Sequence[object]],
        scalar_columns: Sequence[str],
        return_tags: bool = False,
    ):
        result_scalars = defaultdict[str, defaultdict[str, list[tuple[int, float]]]](
            lambda: defaultdict(list)
        )
        result_tags: dict[str, list[StepTagsDTO]] = defaultdict(list)

        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = row[col_index[ProjectTableColumns.EXPERIMENT_ID.value]]
            step = row[col_index[ProjectTableColumns.STEP.value]]
            tags = row[col_index[ProjectTableColumns.TAGS.value]] or []

            row_scalar_names: list[str] = []
            for scalar_name in scalar_columns:
                value = row[col_index[scalar_name]]
                if value is None:
                    continue
                result_scalars[experiment_id][scalar_name].append((step, value))
                row_scalar_names.append(scalar_name)

            if return_tags:
                result_tags[experiment_id].append(
                    StepTagsDTO(
                        step=step,
                        scalar_names=sorted(row_scalar_names),
                        tags=tags,
                    )
                )

        return result_scalars, result_tags

    async def _table_exists(self, table_name: str) -> bool:
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])

    async def _get_table_columns(self, table_name: str) -> list[str]:
        query = SCALARS_DB_UTILS.build_describe_table_statement(table_name)
        result = await self.client.query(query)
        return [row[0] for row in result.result_rows]

    async def _get_scalar_columns(self, table_name: str) -> list[str]:
        columns = await self._get_table_columns(table_name)
        base_columns = set(SCALARS_DB_UTILS.get_base_columns())
        return [col for col in columns if col not in base_columns]

    async def _ensure_table_and_columns(
        self, table_name: str, scalar_columns: Sequence[str]
    ) -> None:
        if not await self._table_exists(table_name):
            ddl = SCALARS_DB_UTILS.build_create_table_statement(
                table_name, scalar_columns=scalar_columns
            )
            await self.client.command(ddl)
            return

        existing_columns = set(await self._get_table_columns(table_name))
        missing = [col for col in scalar_columns if col not in existing_columns]
        if missing:
            ddl = SCALARS_DB_UTILS.build_alter_table_add_columns_statement(
                table_name, missing
            )
            await self.client.command(ddl)

    def _validate_scalar_names(self, names: Sequence[str]) -> list[str]:
        validated = [SCALARS_DB_UTILS.validate_scalar_column_name(name) for name in names]
        return list(validated)

    async def _invalidate_cache(self, project_id: str, experiment_id: str) -> None:
        if self.cache is None:
            return
        # Invalidate cache for the experiment
        cache_key_pattern = _build_scalars_cache_key(
            project_id, experiment_id, "*", "*"
        )
        await self.cache.invalidate(cache_key_pattern)
        # Invalidate cache for all scalars (no experiment id)
        cache_key_pattern = _build_scalars_cache_key(project_id, None, "*", "*")
        await self.cache.invalidate(cache_key_pattern)
