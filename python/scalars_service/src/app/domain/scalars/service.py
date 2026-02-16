from collections import defaultdict
from datetime import datetime, timezone
import json
from typing import Literal, Sequence, cast
from uuid import UUID, uuid4

from app.domain.scalars.dto import (  # type: ignore
    ExperimentsScalarsPointsResultDTO,
    LastLoggedExperimentDTO,
    LastLoggedExperimentsResultDTO,
    LogScalarRequestDTO,
    LogScalarsRequestDTO,
    LogScalarResponseDTO,
    LogScalarsResponseDTO,
    ScalarSeriesDTO,
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
    project_id: UUID,
    experiment_id: UUID | None,
    max_points: int | None | Literal["*"],
    return_tags: bool | Literal["*"],
    start_time: datetime | None | Literal["*"],
    end_time: datetime | None | Literal["*"],
) -> str:
    start_time_key = (
        "*" if start_time == "*" else start_time.isoformat() if start_time else "none"
    )
    end_time_key = (
        "*" if end_time == "*" else end_time.isoformat() if end_time else "none"
    )
    return (
        f"scalars:project:{project_id}:experiment:{experiment_id}:max_points:{max_points}:"
        f"return_tags:{return_tags}:start_time:{start_time_key}:end_time:{end_time_key}"
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


# TODO: Add cache invalidation when scalar is logged (for case when we get all elements from cache (when experiment_id is None)))
class ScalarsService:
    def __init__(self, client, cache: Cache | None = None):
        self.client = client
        self.cache = cache
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
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not await self._table_exists(table_name):
            raise ValueError("Scalars table does not exist")
        # We must invalidate cache because we are logging a scalar for a given experiment.
        if self.cache is not None:
            await self._invalidate_cache(project_id, experiment_id)
        # Filter out conflicting scalars and return warnings if any.
        filtered_scalars, warnings = self._filter_conflicting_scalars(request.scalars)
        if not filtered_scalars:
            return LogScalarResponseDTO(status="logged", warnings=warnings or None)

        # Get or create scalar mapping (because them stored per step and single column per scalar).
        # Table columns can't be random strings, so we need to map them to internal names.

        mapping = await self._get_or_create_scalar_mapping(project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping, filtered_scalars.keys()
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id, mapping)
            # Ensure that the table and columns exist. If not, create them. If columns are missing, add them.
        # Because clickhouse doesn't support transactions, we need to ensure that the table and columns exist before logging the scalar.
        await self._ensure_scalars_columns(table_name, list(mapped_columns.values()))

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        logged_at = _get_now_datetime()
        row = [
            logged_at,
            experiment_id,
            request.step,
            request.tags or [],
        ] + [filtered_scalars[name] for name in mapped_columns.keys()]
        await self.client.insert(table_name, [row], column_names=columns)
        await self._touch_last_logged_experiment(project_id, experiment_id, logged_at)
        return LogScalarResponseDTO(status="logged", warnings=warnings or None)

    async def log_scalars(
        self, project_id: UUID, experiment_id: UUID, request: LogScalarsRequestDTO
    ):
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not await self._table_exists(table_name):
            raise ValueError("Scalars table does not exist")
        if self.cache is not None:
            await self._invalidate_cache(project_id, experiment_id)
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

        all_scalar_names = {name for item in filtered_items for name in item.scalars}
        mapping = await self._get_or_create_scalar_mapping(project_id)
        mapped_columns, mapping_updated = self._resolve_scalar_columns(
            mapping, all_scalar_names
        )
        if mapping_updated:
            await self._save_scalar_mapping(project_id, mapping)
        # Because clickhouse doesn't support transactions, we need to ensure that the table and columns exist before logging the scalar.
        await self._ensure_scalars_columns(table_name, list(mapped_columns.values()))

        columns = SCALARS_DB_UTILS.get_base_columns() + list(mapped_columns.values())
        rows = []
        last_modified = _get_now_datetime()
        for item in filtered_items:
            row = [
                last_modified,
                experiment_id,
                item.step,
                item.tags or [],
            ] + [item.scalars[name] for name in mapped_columns.keys()]
            rows.append(row)
        if rows:
            await self.client.insert(table_name, rows, column_names=columns)
            await self._touch_last_logged_experiment(
                project_id, experiment_id, last_modified
            )
        return LogScalarsResponseDTO(status="logged", warnings=warnings or None)

    async def get_scalars(
        self,
        project_id: UUID,
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None = None,
        max_points: int | None = None,
        return_tags: bool = False,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        """Get scalars for a given project and experiment.

        Args:
            project_id (UUID): The project ID.
            experiment_id (UUID | list[UUID] | tuple[UUID, ...] | None): The experiment ID.
            max_points (int | None): The maximum number of points to return.
            return_tags (bool): Whether to return tags.
            start_time (datetime | None): The start time.
            end_time (datetime | None): The end time.

        Returns:
            ScalarsPointsResultDTO: The scalars points result.
        """
        if max_points is None:
            max_points = self.default_max_points
        if start_time is not None and end_time is not None and start_time > end_time:
            raise ValueError("start_time must be less than or equal to end_time")

        experiment_ids: list[UUID] | None = None
        if experiment_id is not None:
            if isinstance(experiment_id, UUID):
                experiment_ids = [experiment_id]
            else:
                experiment_ids = list(experiment_id)

        # We already defined result as list, because we will append to it in the loop
        result = []
        excluded_experiment_ids: list[UUID] = []
        # Try to get from cache
        if self.cache is not None:
            if experiment_ids is None:
                # Get all scalars from cache
                cache_key = _build_scalars_cache_key(
                    project_id,
                    None,
                    max_points,
                    return_tags,
                    start_time,
                    end_time,
                )
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            else:
                # Get scalars from cache for each experiment id
                for exp_id in experiment_ids:
                    query_cache_key = _build_scalars_cache_key(
                        project_id,
                        exp_id,
                        max_points,
                        return_tags,
                        start_time,
                        end_time,
                    )
                    cached_result = await self.cache.get(query_cache_key)
                    if cached_result is not None:
                        excluded_experiment_ids.append(exp_id)
                        result.append(cached_result)
                if len(result) == len(experiment_ids):
                    return ScalarsPointsResultDTO(data=result)
                experiment_ids = [
                    exp_id
                    for exp_id in experiment_ids
                    if exp_id not in excluded_experiment_ids
                ]

        # If not in cache, get from database
        table_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        if not await self._table_exists(table_name):
            return ScalarsPointsResultDTO(data=result)

        scalar_columns = await self._get_scalar_columns(table_name)
        mapping = await self._get_or_create_scalar_mapping(project_id)
        column_to_scalar_name = {column: scalar for scalar, column in mapping.items()}
        select_statement = SCALARS_DB_UTILS.build_select_statement(
            table_name,
            scalar_columns=scalar_columns,
            experiment_ids=experiment_ids,
            start_time=start_time,
            end_time=end_time,
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
                    project_id,
                    result_item.experiment_id,
                    max_points,
                    return_tags,
                    start_time,
                    end_time,
                )
                await self.cache.set(cache_key, result_item)
            # Set cache for all scalars (no experiment id)
            if experiment_ids is None:
                cache_key = _build_scalars_cache_key(
                    project_id,
                    None,
                    max_points,
                    return_tags,
                    start_time,
                    end_time,
                )
                await self.cache.set(cache_key, response)
        return response

    async def get_last_logged_experiments(
        self, project_id: UUID, experiment_ids: Sequence[UUID] | None = None
    ) -> LastLoggedExperimentsResultDTO:
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        if not await self._table_exists(table_name):
            return LastLoggedExperimentsResultDTO(data=[])
        query = SCALARS_DB_UTILS.build_select_last_logged_statement(
            table_name,
            experiment_ids=experiment_ids,
        )
        result = await self.client.query(query)
        print(result.result_rows)
        data = [
            LastLoggedExperimentDTO(
                experiment_id=cast(UUID, row[0]),
                last_modified=cast(datetime, row[1]).isoformat(),
            )
            for row in result.result_rows
        ]
        return LastLoggedExperimentsResultDTO(data=data)

    def _split_scalars_by_experiment_id(
        self,
        column_names: Sequence[str],
        rows: list[Sequence[object]],
        scalar_columns: Sequence[str],
        column_to_scalar_name: dict[str, str],
        return_tags: bool = False,
    ):
        # experiment id -> scalar name -> scalar series
        result_scalars = defaultdict[UUID, dict[str, ScalarSeriesDTO]](dict)
        # experiment id -> step tags
        result_tags: dict[UUID, list[StepTagsDTO]] = defaultdict(list)

        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = cast(
                UUID, row[col_index[ProjectTableColumns.EXPERIMENT_ID.value]]
            )
            step = cast(int, row[col_index[ProjectTableColumns.STEP.value]])
            # List of tags for the step.
            tags = cast(list[str], row[col_index[ProjectTableColumns.TAGS.value]] or [])
            # List of scalar names for the step.
            row_scalar_names: list[str] = []
            for scalar_name in scalar_columns:
                value = row[col_index[scalar_name]]
                if value is None:
                    continue
                # If name is not in mapping, use original name
                original_name = column_to_scalar_name.get(scalar_name, scalar_name)
                scalar_series = result_scalars[experiment_id].setdefault(
                    original_name,
                    ScalarSeriesDTO(x=[], y=[]),
                )
                scalar_series.x.append(step)
                scalar_series.y.append(cast(float, value))
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
        """Check if the table exists.

        Args:
            table_name (str): The table name.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        # Query returns count of rows > 0 if table exists.
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
        """Filter out conflicting scalars and return warnings if any.
        Keep in mind that scalars are not validated in any way.
        This method is used to filter out scalars that are not valid (uses internal names for scalars).

        Args:
            scalars (dict[str, float]): The scalars to filter.

        Returns:
            tuple[dict[str, float], list[str]]: The filtered scalars and warnings.
        """
        filtered: dict[str, float] = {}
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
        query = SCALARS_DB_UTILS.build_select_mapping_statement(project_id)
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
            SCALARS_DB_UTILS.get_mapping_table_name(),
            [[project_id, payload, _get_now_datetime()]],
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
        mapping = await self._load_scalar_mapping(project_id)
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
            mapping[name] = self._generate_scalar_column_name(existing_columns)
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
        if self.cache is None:
            return
        # Invalidate cache for the experiment
        cache_key_pattern = _build_scalars_cache_key(
            project_id, experiment_id, "*", "*", "*", "*"
        )
        await self.cache.invalidate(cache_key_pattern)
        # Invalidate cache for all scalars (no experiment id)
        cache_key_pattern = _build_scalars_cache_key(
            project_id, None, "*", "*", "*", "*"
        )
        await self.cache.invalidate(cache_key_pattern)

    async def _touch_last_logged_experiment(
        self, project_id: UUID, experiment_id: UUID, last_modified: datetime
    ) -> None:
        """Touch last logged experiment.

        Args:
            project_id (UUID): The project ID.
            experiment_id (UUID): The experiment ID.
            last_modified (datetime): The last modified timestamp.

        Returns:
            None: The function does not return anything.
        """
        table_name = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        statement = SCALARS_DB_UTILS.build_upsert_last_logged_statement(
            table_name, experiment_id, last_modified
        )
        await self.client.command(statement)
