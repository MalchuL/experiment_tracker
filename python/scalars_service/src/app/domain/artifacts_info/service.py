from collections import defaultdict
from datetime import datetime
from typing import Literal, Sequence, cast
from uuid import UUID

from experiment_tracker_shared import utc_naive_for_clickhouse_insert, utc_now_naive

from .dto import (
    ExperimentArtifactsInfoResultDTO,
    ExperimentArtifactsSummaryDTO,
    LogArtifactInfoRequestDTO,
    LogArtifactInfoResponseDTO,
    LogArtifactsInfoRequestDTO,
    LogArtifactsInfoResponseDTO,
    ArtifactInfoEntryDTO,
    ArtifactInfoSummaryEntryDTO,
    ArtifactsInfoResultDTO,
    ArtifactsInfoSummaryResultDTO,
)
from app.domain.projects.dto import ClickhouseTableUsageStats  # type: ignore
from app.domain.utils.scalars_db_utils import (  # type: ignore
    ArtifactsInfoTableColumns,
    SCALARS_DB_UTILS,
)
from app.domain.utils.scalars_select_sql import SCALARS_SELECT_SQL  # type: ignore
from app.domain.last_logged.service import LastLoggedService
from app.infrastructure.cache.cache import Cache  # type: ignore


def _build_artifacts_summary_cache_key(
    project_id: UUID,
    experiment_id: UUID | Literal["*"],
    artifact_types: Sequence[str] | Literal["*"] | None,
    artifact_names: Sequence[str] | Literal["*"] | None,
    max_steps: int | Literal["*"],
) -> str:
    """Build the per-experiment cache key for unbounded artifact summary lookups.

    This mirrors scalar caching: the paginated response itself is not cached. Instead, each
    experiment's artifact-summary payload is stored independently, keyed by the artifact
    name/type filters and ``max_steps``. Passing ``"*"`` creates an invalidation pattern.

    Time-bounded live-refresh queries intentionally skip cache so they always see newly logged rows.
    """

    type_key = (
        "*"
        if artifact_types == "*"
        else ",".join(sorted(artifact_types or [])) or "all"
    )
    name_key = (
        "*"
        if artifact_names == "*"
        else ",".join(sorted(artifact_names or [])) or "all"
    )
    return (
        f"artifacts_info_summary:project:{project_id}:experiment:{experiment_id}:"
        f"types:{type_key}:names:{name_key}:max_steps:{max_steps}"
    )


class ArtifactsInfoService:
    def __init__(
        self,
        client,
        last_logged_service: LastLoggedService | None = None,
        cache: Cache | None = None,
    ):
        self.client = client
        self.last_logged_service = last_logged_service
        self.cache = cache

    async def log_artifact_info(
        self, project_id: UUID, experiment_id: UUID, request: LogArtifactInfoRequestDTO
    ) -> LogArtifactInfoResponseDTO:
        # Objects metadata is stored in a dedicated per-project table: objects_{project_id}.
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        await self._ensure_artifacts_info_table(project_id)
        warnings = self._validate_artifact_info_request(request)
        if warnings:
            return LogArtifactInfoResponseDTO(status="logged", warnings=warnings)
        logged_at = utc_now_naive()
        row = [
            utc_naive_for_clickhouse_insert(logged_at),
            experiment_id,
            request.step,
            request.name,
            request.artifact_type,
            request.path,
            request.metadata or {},
            request.tags or [],
        ]
        await self.client.insert(
            table_name,
            [row],
            column_names=[
                ArtifactsInfoTableColumns.TIMESTAMP.value,
                ArtifactsInfoTableColumns.EXPERIMENT_ID.value,
                ArtifactsInfoTableColumns.STEP.value,
                ArtifactsInfoTableColumns.NAME.value,
                ArtifactsInfoTableColumns.ARTIFACT_TYPE.value,
                ArtifactsInfoTableColumns.PATH.value,
                ArtifactsInfoTableColumns.METADATA.value,
                ArtifactsInfoTableColumns.TAGS.value,
            ],
        )
        if self.last_logged_service:
            await self.last_logged_service.touch(project_id, experiment_id, logged_at)
        await self._invalidate_summary_cache(project_id, experiment_id)
        return LogArtifactInfoResponseDTO(status="logged")

    async def log_artifact_info_batch(
        self, project_id: UUID, experiment_id: UUID, request: LogArtifactsInfoRequestDTO
    ) -> LogArtifactsInfoResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        await self._ensure_artifacts_info_table(project_id)
        if not request.artifacts:
            return LogArtifactsInfoResponseDTO(status="logged")
        rows = []
        warnings: list[str] = []
        last_modified = utc_now_naive()
        wire_ts = utc_naive_for_clickhouse_insert(last_modified)
        for item in request.artifacts:
            # Keep batch writes robust: invalid rows are skipped with warnings, not hard-failed.
            item_warnings = self._validate_artifact_info_request(item)
            warnings.extend(item_warnings)
            if item_warnings:
                continue
            rows.append(
                [
                    wire_ts,
                    experiment_id,
                    item.step,
                    item.name,
                    item.artifact_type,
                    item.path,
                    item.metadata or {},
                    item.tags or [],
                ]
            )
        if rows:
            await self.client.insert(
                table_name,
                rows,
                column_names=[
                    ArtifactsInfoTableColumns.TIMESTAMP.value,
                    ArtifactsInfoTableColumns.EXPERIMENT_ID.value,
                    ArtifactsInfoTableColumns.STEP.value,
                    ArtifactsInfoTableColumns.NAME.value,
                    ArtifactsInfoTableColumns.ARTIFACT_TYPE.value,
                    ArtifactsInfoTableColumns.PATH.value,
                    ArtifactsInfoTableColumns.METADATA.value,
                    ArtifactsInfoTableColumns.TAGS.value,
                ],
            )
            if self.last_logged_service:
                await self.last_logged_service.touch(
                    project_id, experiment_id, last_modified
                )
            await self._invalidate_summary_cache(project_id, experiment_id)
        return LogArtifactsInfoResponseDTO(status="logged", warnings=warnings or None)

    async def get_artifacts_info(
        self,
        project_id: UUID,
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        steps: list[int] | None = None,
        limit: int = 100,
        offset: int = 0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ArtifactsInfoResultDTO:
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        if not await self._table_exists(table_name):
            return ArtifactsInfoResultDTO(data=[], has_next=False, size=0, total=0)
        experiment_ids: list[UUID] | None = None
        if experiment_id is not None:
            if isinstance(experiment_id, UUID):
                experiment_ids = [experiment_id]
            else:
                experiment_ids = list(experiment_id)
        query = SCALARS_DB_UTILS.build_select_artifacts_info_statement(
            table_name,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            names=artifact_names,
            steps=steps,
            start_time=start_time,
            end_time=end_time,
        )
        result = await self.client.query(query)
        # Response shape is grouped by experiment to match frontend rendering model.
        grouped = self._group_artifacts_info_by_experiment(
            result.column_names, result.result_rows
        )
        grouped_items = [
            ExperimentArtifactsInfoResultDTO(
                experiment_id=exp_id, artifacts_info=artifacts_info
            )
            for exp_id, artifacts_info in grouped.items()
        ]
        total = len(grouped_items)
        page = grouped_items[offset : offset + limit]
        return ArtifactsInfoResultDTO(
            data=page,
            has_next=offset + len(page) < total,
            size=len(page),
            total=total,
        )

    async def get_artifacts_info_summary(
        self,
        project_id: UUID,
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        max_steps: int = 1000,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ArtifactsInfoSummaryResultDTO:
        """Return lightweight per-experiment artifact groups for slider construction.

        The ClickHouse query samples up to ``max_steps`` steps per
        ``(experiment_id, artifact_type, name)`` group. Unbounded queries cache one
        experiment summary at a time, matching the scalar service's per-experiment cache strategy.
        Bounded queries are used for live refresh and skip cache.
        """

        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        if not await self._table_exists(table_name):
            return ArtifactsInfoSummaryResultDTO(
                data=[], has_next=False, size=0, total=0
            )
        experiment_ids, browse_all = self._normalize_experiment_id_filter(
            experiment_id
        )
        if browse_all:
            total_experiments, page_ids = (
                await self._clickhouse_distinct_artifact_experiment_page(
                    table_name=table_name,
                    artifact_types=artifact_types,
                    artifact_names=artifact_names,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    offset=offset,
                )
            )
        else:
            assert experiment_ids is not None
            total_experiments, page_ids = self._explicit_experiment_page_slice(
                requested_ids=experiment_ids,
                limit=limit,
                offset=offset,
            )

        cached_full, cached_by_exp = await self._get_artifacts_summary_try_cache(
            project_id=project_id,
            page_ids=page_ids,
            total_experiments=total_experiments,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            max_steps=max_steps,
            limit=limit,
            offset=offset,
            start_time=start_time,
            end_time=end_time,
        )
        if cached_full is not None:
            return cached_full

        ids_to_fetch = [eid for eid in page_ids if eid not in cached_by_exp]
        grouped: dict[UUID, list[ArtifactInfoSummaryEntryDTO]] = {}
        if ids_to_fetch:
            query = SCALARS_DB_UTILS.build_select_artifacts_info_summary_statement(
                table_name,
                experiment_ids=ids_to_fetch,
                artifact_types=artifact_types,
                names=artifact_names,
                start_time=start_time,
                end_time=end_time,
                max_steps=max_steps,
            )
            result = await self.client.query(query)
            grouped = self._group_artifacts_summary_by_experiment(
                result.column_names, result.result_rows
            )
        merged = self._assemble_artifacts_summary_page(
            page_ids=page_ids,
            cached_by_exp=cached_by_exp,
            grouped=grouped,
        )
        response = ArtifactsInfoSummaryResultDTO(
            data=merged,
            has_next=offset + len(page_ids) < total_experiments,
            size=len(merged),
            total=total_experiments,
        )
        await self._store_artifacts_summary_cache(
            project_id=project_id,
            merged=merged,
            skip_experiment_ids=frozenset(cached_by_exp),
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            max_steps=max_steps,
            start_time=start_time,
            end_time=end_time,
        )
        return response

    def _normalize_experiment_id_filter(
        self, experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None
    ) -> tuple[list[UUID] | None, bool]:
        """Split summary input into explicit experiment ids vs project-wide browsing."""
        if experiment_id is None:
            return None, True
        if isinstance(experiment_id, UUID):
            return [experiment_id], False
        return list(experiment_id), False

    @staticmethod
    def _explicit_experiment_page_slice(
        requested_ids: list[UUID], limit: int, offset: int
    ) -> tuple[int, list[UUID]]:
        """Page an explicit experiment-id filter without asking ClickHouse for ids."""
        return len(requested_ids), requested_ids[offset : offset + limit]

    async def _clickhouse_distinct_artifact_experiment_page(
        self,
        table_name: str,
        artifact_types: list[str] | None,
        artifact_names: list[str] | None,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[UUID]]:
        """Count and page experiments that have artifact_info rows for the summary filters."""
        count_sql = SCALARS_DB_UTILS.build_count_distinct_artifact_experiments_statement(
            table_name=table_name,
            artifact_types=artifact_types,
            names=artifact_names,
            start_time=start_time,
            end_time=end_time,
        )
        count_result = await self.client.query(count_sql)
        total = int(count_result.result_rows[0][0])
        page_sql = SCALARS_DB_UTILS.build_select_artifact_experiment_id_page_statement(
            table_name=table_name,
            artifact_types=artifact_types,
            names=artifact_names,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        page_result = await self.client.query(page_sql)
        page_ids = [cast(UUID, row[0]) for row in page_result.result_rows]
        return total, page_ids

    async def _get_artifacts_summary_try_cache(
        self,
        project_id: UUID,
        page_ids: list[UUID],
        total_experiments: int,
        artifact_types: list[str] | None,
        artifact_names: list[str] | None,
        max_steps: int,
        limit: int,
        offset: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> tuple[
        ArtifactsInfoSummaryResultDTO | None,
        dict[UUID, ExperimentArtifactsSummaryDTO],
    ]:
        """Return a cached artifact summary page or partial per-experiment hits."""
        if self.cache is None:
            return None, {}
        if start_time is not None or end_time is not None:
            return None, {}

        cached_by_exp: dict[UUID, ExperimentArtifactsSummaryDTO] = {}
        for exp_id in page_ids:
            ck = _build_artifacts_summary_cache_key(
                project_id=project_id,
                experiment_id=exp_id,
                artifact_types=artifact_types,
                artifact_names=artifact_names,
                max_steps=max_steps,
            )
            row = await self.cache.get(key=ck)
            if isinstance(row, ExperimentArtifactsSummaryDTO):
                cached_by_exp[exp_id] = row

        if len(cached_by_exp) != len(page_ids):
            return None, cached_by_exp

        ordered = [cached_by_exp[eid] for eid in page_ids]
        return (
            ArtifactsInfoSummaryResultDTO(
                data=ordered,
                has_next=offset + len(page_ids) < total_experiments,
                size=len(ordered),
                total=total_experiments,
            ),
            {},
        )

    @staticmethod
    def _assemble_artifacts_summary_page(
        page_ids: list[UUID],
        cached_by_exp: dict[UUID, ExperimentArtifactsSummaryDTO],
        grouped: dict[UUID, list[ArtifactInfoSummaryEntryDTO]],
    ) -> list[ExperimentArtifactsSummaryDTO]:
        """Build a page from cached rows and newly loaded artifact summary groups."""
        merged: list[ExperimentArtifactsSummaryDTO] = []
        for exp_id in page_ids:
            if exp_id in cached_by_exp:
                merged.append(cached_by_exp[exp_id])
                continue
            merged.append(
                ExperimentArtifactsSummaryDTO(
                    experiment_id=exp_id,
                    artifacts_info=grouped.get(exp_id, []),
                )
            )
        return merged

    async def _store_artifacts_summary_cache(
        self,
        project_id: UUID,
        merged: list[ExperimentArtifactsSummaryDTO],
        skip_experiment_ids: frozenset[UUID],
        artifact_types: list[str] | None,
        artifact_names: list[str] | None,
        max_steps: int,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> None:
        """Persist per-experiment artifact summaries for unbounded queries only."""
        if self.cache is None:
            return
        if start_time is not None or end_time is not None:
            return
        for item in merged:
            if item.experiment_id in skip_experiment_ids:
                continue
            ck = _build_artifacts_summary_cache_key(
                project_id=project_id,
                experiment_id=item.experiment_id,
                artifact_types=artifact_types,
                artifact_names=artifact_names,
                max_steps=max_steps,
            )
            await self.cache.set(key=ck, value=item)

    async def get_artifacts_info_detail(
        self,
        project_id: UUID,
        experiment_id: UUID,
        artifact_name: str,
        step: int,
        artifact_type: str | None = None,
    ) -> ArtifactsInfoResultDTO:
        """Return the current full DTO shape for exactly one artifact name/step lookup.

        This is the lazy-detail companion to ``get_artifacts_info_summary``. Callers use it after
        a slider step is selected to recover path, metadata, tags, and timestamp for download/cache
        busting without loading every artifact_info row up front.
        """

        result = await self.get_artifacts_info(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_types=[artifact_type] if artifact_type else None,
            artifact_names=[artifact_name],
            steps=[step],
            limit=1,
            offset=0,
        )
        entries = [
            entry
            for group in result.data
            for entry in group.artifacts_info
            if entry.name == artifact_name
            and entry.step == step
            and (artifact_type is None or entry.artifact_type == artifact_type)
        ]
        if not entries:
            raise LookupError("artifact info not found")
        return ArtifactsInfoResultDTO(
            data=[
                ExperimentArtifactsInfoResultDTO(
                    experiment_id=experiment_id, artifacts_info=[entries[0]]
                )
            ],
            has_next=False,
            size=1,
            total=1,
        )

    def _normalize_experiment_ids(
        self, experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None
    ) -> list[UUID] | None:
        if experiment_id is None:
            return None
        if isinstance(experiment_id, UUID):
            return [experiment_id]
        return list(experiment_id)

    def _group_artifacts_info_by_experiment(
        self, column_names: Sequence[str], rows: list[Sequence[object]]
    ) -> dict[UUID, list[ArtifactInfoEntryDTO]]:
        data = defaultdict[UUID, list[ArtifactInfoEntryDTO]](list)
        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = cast(
                UUID, row[col_index[ArtifactsInfoTableColumns.EXPERIMENT_ID.value]]
            )
            data[experiment_id].append(
                ArtifactInfoEntryDTO(
                    timestamp=cast(
                        datetime,
                        row[col_index[ArtifactsInfoTableColumns.TIMESTAMP.value]],
                    ),
                    step=cast(
                        int, row[col_index[ArtifactsInfoTableColumns.STEP.value]]
                    ),
                    name=cast(
                        str, row[col_index[ArtifactsInfoTableColumns.NAME.value]]
                    ),
                    artifact_type=cast(
                        str,
                        row[col_index[ArtifactsInfoTableColumns.ARTIFACT_TYPE.value]],
                    ),
                    path=cast(
                        str, row[col_index[ArtifactsInfoTableColumns.PATH.value]]
                    ),
                    metadata=cast(
                        dict[str, str],
                        row[col_index[ArtifactsInfoTableColumns.METADATA.value]] or {},
                    ),
                    tags=cast(
                        list[str],
                        row[col_index[ArtifactsInfoTableColumns.TAGS.value]] or [],
                    ),
                )
            )
        return data

    def _group_artifacts_summary_by_experiment(
        self, column_names: Sequence[str], rows: list[Sequence[object]]
    ) -> dict[UUID, list[ArtifactInfoSummaryEntryDTO]]:
        """Map ClickHouse summary rows into the public grouped-by-experiment DTO shape."""

        data = defaultdict[UUID, list[ArtifactInfoSummaryEntryDTO]](list)
        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = cast(
                UUID, row[col_index[ArtifactsInfoTableColumns.EXPERIMENT_ID.value]]
            )
            data[experiment_id].append(
                ArtifactInfoSummaryEntryDTO(
                    name=cast(
                        str, row[col_index[ArtifactsInfoTableColumns.NAME.value]]
                    ),
                    artifact_type=cast(
                        str,
                        row[col_index[ArtifactsInfoTableColumns.ARTIFACT_TYPE.value]],
                    ),
                    steps=[
                        int(step)
                        for step in cast(
                            Sequence[int],
                            row[col_index["steps"]],
                        )
                    ],
                    # last_modified is the maximum timestamp of the steps, there is no relation with last_logged
                    last_modified=cast(datetime, row[col_index["last_modified"]]),
                )
            )
        return data

    def _validate_artifact_info_request(
        self, request: LogArtifactInfoRequestDTO
    ) -> list[str]:
        warnings: list[str] = []
        if not request.name.strip():
            warnings.append("Artifact name is empty and was skipped.")
        if not request.path.strip():
            warnings.append("Artifact path is empty and was skipped.")
        return warnings

    async def _ensure_artifacts_info_table(self, project_id: UUID) -> None:
        """Ensure the artifacts info table exists. Create it if it does not."""
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        if not await self._table_exists(table_name):
            ddl = SCALARS_DB_UTILS.build_create_artifacts_info_table_statement(
                table_name
            )
            await self.client.command(ddl)

    async def _invalidate_summary_cache(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        """Clear artifact summary cache entries for one experiment after writes/deletes."""

        if self.cache is None:
            return
        cache_key_pattern = _build_artifacts_summary_cache_key(
            project_id=project_id,
            experiment_id=experiment_id,
            artifact_types="*",
            artifact_names="*",
            max_steps="*",
        )
        await self.cache.invalidate(pattern=cache_key_pattern)

    async def _table_exists(self, table_name: str) -> bool:
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])

    async def create_clickhouse_table(self, project_id: UUID) -> str:
        """Run DDL for this project's artifacts_info table."""
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        ddl = SCALARS_DB_UTILS.build_create_artifacts_info_table_statement(table_name)
        await self.client.command(ddl)
        return table_name

    async def drop_clickhouse_table(self, project_id: UUID) -> None:
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )

    async def delete_experiment_rows_if_table_exists(
        self, project_id: UUID, experiment_id: UUID
    ) -> None:
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        if not await self._table_exists(table_name):
            return
        await self.client.command(
            SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
                table_name=table_name,
                experiment_id=experiment_id,
                experiment_id_column=ArtifactsInfoTableColumns.EXPERIMENT_ID.value,
            )
        )
        await self._invalidate_summary_cache(project_id, experiment_id)

    async def get_clickhouse_table_usage_stats(
        self, project_id: UUID
    ) -> ClickhouseTableUsageStats:
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        if not await self._table_exists(table_name):
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

    async def drop_managed_table_by_name(self, table_name: str) -> None:
        if not table_name.startswith("artifacts_info_"):
            raise ValueError("Only scalar-service managed tables can be dropped")
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Invalid table name")
        await self.client.command(
            SCALARS_DB_UTILS.build_drop_table_statement(table_name)
        )
