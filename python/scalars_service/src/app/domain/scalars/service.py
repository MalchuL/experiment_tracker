from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal
from app.domain.scalars.dto import (
    ExperimentsScalarsPointsResultDTO,
    LogScalarRequestDTO,
    ScalarsPointsResultDTO,
    LogScalarResponseDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS, ProjectTableColumns
import asyncpg
import json
from app.infrastructure.cache.cache import Cache


def _check_is_none(value: any) -> bool:
    return value is None or value == "null" or value == "None"


def _get_now_datetime() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_scalars_cache_key(
    project_id: str,
    experiment_id: str | None,
    max_points: int | None | Literal["*"],
    return_tags: bool | Literal["*"],
) -> str:
    return f"scalars:project:{project_id}:experiment:{experiment_id}:max_points:{max_points}:return_tags:{return_tags}"


# TODO: Add cache invalidation when scalar is logged (for case when we get all elements from cache)
class ScalarsService:
    def __init__(self, conn: asyncpg.Connection, cache: Cache | None = None):
        self.conn = conn
        self.cache = cache
        self.default_max_points: int = 1000

    async def log_scalar(
        self, project_id: str, experiment_id: str, request: LogScalarRequestDTO
    ):
        if self.cache is not None:
            # Invalidate cache for the experiment
            cache_key_pattern = _build_scalars_cache_key(
                project_id, experiment_id, "*", "*"
            )
            await self.cache.invalidate(cache_key_pattern)
            # Invalidate cache for all scalars (no experiment id)
            cache_key_pattern = _build_scalars_cache_key(project_id, None, "*", "*")
            await self.cache.invalidate(cache_key_pattern)

        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        timestamp = _get_now_datetime()
        await self.conn.execute(
            SCALARS_DB_UTILS.build_insert_statement(table_name),
            timestamp,
            experiment_id,
            request.scalar_name,
            request.value,
            request.step,
            json.dumps(request.tags),
        )
        return LogScalarResponseDTO(status="logged")

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

        # Try to get from cache
        if self.cache is not None:
            excluded_experiment_ids = []
            cached_results = []

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
                        cached_results.append(cached_result)
                if len(cached_results) == len(experiment_id):
                    return ScalarsPointsResultDTO(data=cached_results)

        # If not in cache, get from database
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if experiment_id is not None:
            if len(excluded_experiment_ids) > 0:
                experiment_id = [
                    exp_id
                    for exp_id in experiment_id
                    if exp_id not in excluded_experiment_ids
                ]
            select_statement = (
                SCALARS_DB_UTILS.build_select_statement_with_experiment_ids(
                    table_name, experiment_id
                )
            )
        else:
            select_statement = SCALARS_DB_UTILS.build_select_statement(table_name)
        scalars = await self.conn.fetch(select_statement)
        result_scalars, result_tags = self._split_scalars_by_experiment_id(
            scalars, return_tags
        )

        result = []
        for exp_id, scalars in result_scalars.items():
            result_item = ExperimentsScalarsPointsResultDTO(
                experiment_id=exp_id,
                scalars=scalars,
                tags=result_tags[exp_id],
            )
            result.append(result_item)

        response = ScalarsPointsResultDTO(data=result)

        # Cache results
        if self.cache is not None:
            # Set cache for each experiment id
            for result_item in result:
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
        self, scalars: list[dict], return_tags: bool = False
    ):
        result_scalars = defaultdict(list)
        result_tags = defaultdict(list)
        for scalar in scalars:
            result_scalars[scalar[ProjectTableColumns.EXPERIMENT_ID.value]].append(
                (
                    scalar[ProjectTableColumns.STEP.value],
                    scalar[ProjectTableColumns.VALUE.value],
                )
            )
            if return_tags and not _check_is_none(
                scalar[ProjectTableColumns.TAGS.value]
            ):
                result_tags[scalar[ProjectTableColumns.EXPERIMENT_ID.value]].append(
                    (
                        scalar[ProjectTableColumns.STEP.value],
                        json.loads(scalar[ProjectTableColumns.TAGS.value]),
                    )
                )

        return result_scalars, result_tags
