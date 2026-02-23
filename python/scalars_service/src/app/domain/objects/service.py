from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence, cast
from uuid import UUID

from app.domain.objects.dto import (  # type: ignore
    ExperimentObjectsResultDTO,
    LogObjectRequestDTO,
    LogObjectResponseDTO,
    LogObjectsRequestDTO,
    LogObjectsResponseDTO,
    ObjectEntryDTO,
    ObjectsResultDTO,
)
from app.domain.utils.scalars_db_utils import (  # type: ignore
    ObjectsTableColumns,
    SCALARS_DB_UTILS,
)


def _get_now_datetime() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ObjectsService:
    def __init__(self, client):
        self.client = client

    async def log_object(
        self, project_id: UUID, experiment_id: UUID, request: LogObjectRequestDTO
    ) -> LogObjectResponseDTO:
        # Objects metadata is stored in a dedicated per-project table: objects_{project_id}.
        table_name = SCALARS_DB_UTILS.safe_objects_table_name(project_id)
        if not await self._table_exists(table_name):
            raise ValueError("Objects table does not exist")
        warnings = self._validate_object_request(request)
        if warnings:
            return LogObjectResponseDTO(status="logged", warnings=warnings)
        logged_at = _get_now_datetime()
        row = [
            logged_at,
            experiment_id,
            request.step,
            request.name,
            request.object_type,
            request.path,
            request.metadata or {},
            request.tags or [],
        ]
        await self.client.insert(
            table_name,
            [row],
            column_names=[
                ObjectsTableColumns.TIMESTAMP.value,
                ObjectsTableColumns.EXPERIMENT_ID.value,
                ObjectsTableColumns.STEP.value,
                ObjectsTableColumns.NAME.value,
                ObjectsTableColumns.OBJECT_TYPE.value,
                ObjectsTableColumns.PATH.value,
                ObjectsTableColumns.METADATA.value,
                ObjectsTableColumns.TAGS.value,
            ],
        )
        return LogObjectResponseDTO(status="logged")

    async def log_objects(
        self, project_id: UUID, experiment_id: UUID, request: LogObjectsRequestDTO
    ) -> LogObjectsResponseDTO:
        table_name = SCALARS_DB_UTILS.safe_objects_table_name(project_id)
        if not await self._table_exists(table_name):
            raise ValueError("Objects table does not exist")
        if not request.objects:
            return LogObjectsResponseDTO(status="logged")
        rows = []
        warnings: list[str] = []
        for item in request.objects:
            # Keep batch writes robust: invalid rows are skipped with warnings, not hard-failed.
            item_warnings = self._validate_object_request(item)
            warnings.extend(item_warnings)
            if item_warnings:
                continue
            rows.append(
                [
                    _get_now_datetime(),
                    experiment_id,
                    item.step,
                    item.name,
                    item.object_type,
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
                    ObjectsTableColumns.TIMESTAMP.value,
                    ObjectsTableColumns.EXPERIMENT_ID.value,
                    ObjectsTableColumns.STEP.value,
                    ObjectsTableColumns.NAME.value,
                    ObjectsTableColumns.OBJECT_TYPE.value,
                    ObjectsTableColumns.PATH.value,
                    ObjectsTableColumns.METADATA.value,
                    ObjectsTableColumns.TAGS.value,
                ],
            )
        return LogObjectsResponseDTO(status="logged", warnings=warnings or None)

    async def get_objects(
        self,
        project_id: UUID,
        experiment_id: UUID | list[UUID] | tuple[UUID, ...] | None = None,
        object_types: list[str] | None = None,
        names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ObjectsResultDTO:
        table_name = SCALARS_DB_UTILS.safe_objects_table_name(project_id)
        if not await self._table_exists(table_name):
            return ObjectsResultDTO(data=[])
        experiment_ids: list[UUID] | None = None
        if experiment_id is not None:
            if isinstance(experiment_id, UUID):
                experiment_ids = [experiment_id]
            else:
                experiment_ids = list(experiment_id)
        query = SCALARS_DB_UTILS.build_select_objects_statement(
            table_name,
            experiment_ids=experiment_ids,
            object_types=object_types,
            names=names,
            start_time=start_time,
            end_time=end_time,
        )
        result = await self.client.query(query)
        # Response shape is grouped by experiment to match frontend rendering model.
        grouped = self._group_objects_by_experiment(result.column_names, result.result_rows)
        return ObjectsResultDTO(
            data=[
                ExperimentObjectsResultDTO(experiment_id=exp_id, objects=objects)
                for exp_id, objects in grouped.items()
            ]
        )

    def _group_objects_by_experiment(
        self, column_names: Sequence[str], rows: list[Sequence[object]]
    ) -> dict[UUID, list[ObjectEntryDTO]]:
        data = defaultdict[UUID, list[ObjectEntryDTO]](list)
        col_index = {name: idx for idx, name in enumerate(column_names)}
        for row in rows:
            experiment_id = cast(
                UUID, row[col_index[ObjectsTableColumns.EXPERIMENT_ID.value]]
            )
            data[experiment_id].append(
                ObjectEntryDTO(
                    timestamp=cast(
                        datetime, row[col_index[ObjectsTableColumns.TIMESTAMP.value]]
                    ),
                    step=cast(int, row[col_index[ObjectsTableColumns.STEP.value]]),
                    name=cast(str, row[col_index[ObjectsTableColumns.NAME.value]]),
                    object_type=cast(
                        str, row[col_index[ObjectsTableColumns.OBJECT_TYPE.value]]
                    ),
                    path=cast(str, row[col_index[ObjectsTableColumns.PATH.value]]),
                    metadata=cast(
                        dict[str, str],
                        row[col_index[ObjectsTableColumns.METADATA.value]] or {},
                    ),
                    tags=cast(
                        list[str], row[col_index[ObjectsTableColumns.TAGS.value]] or []
                    ),
                )
            )
        return data

    def _validate_object_request(self, request: LogObjectRequestDTO) -> list[str]:
        warnings: list[str] = []
        if not request.name.strip():
            warnings.append("Object name is empty and was skipped.")
        if not request.path.strip():
            warnings.append("Object path is empty and was skipped.")
        return warnings

    async def _table_exists(self, table_name: str) -> bool:
        query = SCALARS_DB_UTILS.build_table_existence_statement(table_name)
        result = await self.client.query(query)
        return bool(result.result_rows[0][0])
