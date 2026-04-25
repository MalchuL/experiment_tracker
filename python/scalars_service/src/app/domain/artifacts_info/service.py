from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence, cast
from uuid import UUID

from .dto import (
    ExperimentArtifactsInfoResultDTO,
    LogArtifactInfoRequestDTO,
    LogArtifactInfoResponseDTO,
    LogArtifactsInfoRequestDTO,
    LogArtifactsInfoResponseDTO,
    ArtifactInfoEntryDTO,
    ArtifactsInfoResultDTO,
)
from app.domain.utils.scalars_db_utils import (  # type: ignore
    ArtifactsInfoTableColumns,
    SCALARS_DB_UTILS,
)
from app.domain.last_logged.service import LastLoggedService


def _get_now_datetime() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ArtifactsInfoService:
    def __init__(self, client, last_logged_service: LastLoggedService | None = None):
        self.client = client
        self.last_logged_service = last_logged_service

    async def log_artifact_info(
        self, project_id: UUID, experiment_id: UUID, request: LogArtifactInfoRequestDTO
    ) -> LogArtifactInfoResponseDTO:
        # Objects metadata is stored in a dedicated per-project table: objects_{project_id}.
        table_name = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        await self._ensure_artifacts_info_table(project_id)
        warnings = self._validate_artifact_info_request(request)
        if warnings:
            return LogArtifactInfoResponseDTO(status="logged", warnings=warnings)
        logged_at = _get_now_datetime()
        row = [
            logged_at,
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
        last_modified = _get_now_datetime()
        for item in request.artifacts:
            # Keep batch writes robust: invalid rows are skipped with warnings, not hard-failed.
            item_warnings = self._validate_artifact_info_request(item)
            warnings.extend(item_warnings)
            if item_warnings:
                continue
            rows.append(
                [
                    last_modified,
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
            last_modified = _get_now_datetime()
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

    async def _table_exists(self, table_name: str) -> bool:
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])
