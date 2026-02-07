from collections import defaultdict
from datetime import datetime, timezone
import json
from typing import Literal, Sequence, cast
from uuid import uuid4

from app.domain.scalars.dto import (  # type: ignore
    ExperimentsScalarsPointsResultDTO,
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    LogScalarResponseDTO,
    LogScalarsResponseDTO,
    ScalarsPointsResultDTO,
    StepTagsDTO,
)
from app.domain.utils.scalars_db_utils import (  # type: ignore
    SCALARS_DB_UTILS,
    ProjectTableColumns,
)
from app.infrastructure.cache.cache import Cache  # type: ignore


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

        filtered_scalars, warnings = self._filter_conflicting_scalars(request.scalars)
        if not filtered_scalars:
            return LogScalarResponseDTO(status="logged", warnings=warnings or None)

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        mapping = await self._get_or_create_scalar_mapping(project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping, list(filtered_scalars.keys())
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id, mapping)
        await self._ensure_table_and_columns(table_name, list(mapped_columns.values()))

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        row = [
            _get_now_datetime(),
            experiment_id,
            request.step,
            request.tags or [],
        ] + [filtered_scalars[name] for name in mapped_columns.keys()]
        await self.client.insert(table_name, [row], column_names=columns)
        return LogScalarResponseDTO(status="logged", warnings=warnings or None)

    async def log_scalars(
        self, project_id: str, experiment_id: str, request: LogScalarsRequestDTO
    ):
        if self.cache is not None:
            await self._invalidate_cache(project_id, experiment_id)

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not request.scalars:
            return LogScalarsResponseDTO(status="logged")

        warnings: list[str] = []
        filtered_items: list[LogScalarRequestDTO] = []
        for item in request.scalars:
            filtered_scalars, item_warnings = self._filter_conflicting_scalars(
                item.scalars
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

        all_scalar_names = sorted(
            {name for item in filtered_items for name in item.scalars}
        )
        mapping = await self._get_or_create_scalar_mapping(project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping, all_scalar_names
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id, mapping)
        await self._ensure_table_and_columns(table_name, list(mapped_columns.values()))

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        rows = []
        for item in filtered_items:
            row = [
                _get_now_datetime(),
                experiment_id,
                item.step,
                item.tags or [],
            ] + [item.scalars.get(name) for name in mapped_columns.keys()]
            rows.append(row)
        if rows:
            await self.client.insert(table_name, rows, column_names=columns)
        return LogScalarsResponseDTO(status="logged", warnings=warnings or None)

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
        mapping = await self._get_or_create_scalar_mapping(project_id)
        column_to_scalar_name = {column: scalar for scalar, column in mapping.items()}
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
            column_to_scalar_name,
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
        column_to_scalar_name: dict[str, str],
        return_tags: bool = False,
    ):
        result_scalars = defaultdict[str, defaultdict[str, list[tuple[int, float]]]](
            lambda: defaultdict(list)
        )
        result_tags: dict[str, list[StepTagsDTO]] = defaultdict(list)

        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = cast(
                str, row[col_index[ProjectTableColumns.EXPERIMENT_ID.value]]
            )
            step = cast(int, row[col_index[ProjectTableColumns.STEP.value]])
            tags = cast(list[str], row[col_index[ProjectTableColumns.TAGS.value]] or [])

            row_scalar_names: list[str] = []
            for scalar_name in scalar_columns:
                value = row[col_index[scalar_name]]
                if value is None:
                    continue
                # If name is not in mapping, use original name
                original_name = column_to_scalar_name.get(scalar_name, scalar_name)
                result_scalars[experiment_id][original_name].append(
                    (step, cast(float, value))
                )
                row_scalar_names.append(original_name)

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

    def _filter_conflicting_scalars(
        self, scalars: dict[str, float]
    ) -> tuple[dict[str, float], list[str]]:
        filtered: dict[str, float] = {}
        warnings: list[str] = []
        for name, value in scalars.items():
            if not name or not name.strip():
                warnings.append("Scalar name is empty and was skipped.")
                continue
            filtered[name] = value
        return filtered, warnings

    async def _load_scalar_mapping(self, project_id: str) -> dict[str, str] | None:
        query = SCALARS_DB_UTILS.build_select_mapping_statement(project_id)
        result = await self.client.query(query)
        if not result.result_rows:
            return None
        mapping_json = result.result_rows[0][0]
        if not mapping_json:
            return {}
        try:
            parsed = json.loads(mapping_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(k): str(v) for k, v in parsed.items()}

    async def _save_scalar_mapping(
        self, project_id: str, mapping: dict[str, str]
    ) -> None:
        payload = json.dumps(mapping, separators=(",", ":"), sort_keys=True)
        await self.client.insert(
            SCALARS_DB_UTILS.get_mapping_table_name(),
            [[project_id, payload, _get_now_datetime()]],
            column_names=["project_id", "mapping", "updated_at"],
        )

    async def _get_or_create_scalar_mapping(self, project_id: str) -> dict[str, str]:
        mapping = await self._load_scalar_mapping(project_id)
        if mapping is None:
            mapping = {}
        return mapping

    def _resolve_scalar_columns(
        self, mapping: dict[str, str], scalar_names: Sequence[str]
    ) -> tuple[dict[str, str], bool]:
        updated = False
        existing_columns = set(mapping.values())
        resolved: dict[str, str] = {}
        for name in scalar_names:
            if name in mapping:
                resolved[name] = mapping[name]
                continue
            mapping[name] = self._generate_scalar_column_name(existing_columns)
            existing_columns.add(mapping[name])
            resolved[name] = mapping[name]
            updated = True
        return resolved, updated

    def _generate_scalar_column_name(self, existing_columns: set[str]) -> str:
        while True:
            candidate = f"c_{uuid4().hex}"
            if candidate not in existing_columns:
                return candidate

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
