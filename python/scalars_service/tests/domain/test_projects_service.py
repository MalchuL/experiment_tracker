"""Unit tests for ``ProjectsService`` cross-table ClickHouse orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.projects.dto import (
    StorageTableRowDTO,
    ClickhouseTableUsageStats,
    ExperimentClickhouseUsageResponseDTO,
    ListStorageTablesResponseDTO,
)
from app.domain.projects.service import ProjectsService
from app.domain.scalars.dto import CompactProjectColumnsResponseDTO
from app.domain.scalars.service import ScalarsService
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore


@pytest.fixture
def mock_scalars_service() -> MagicMock:
    scalars = MagicMock()
    scalars.compact_project_columns = AsyncMock(
        return_value=CompactProjectColumnsResponseDTO(dropped_columns=[])
    )
    scalars.invalidate_cache_for_experiment = AsyncMock()
    scalars.delete_experiment_rows_if_table_exists = AsyncMock()
    return scalars


@pytest.fixture
def mock_artifacts_service() -> MagicMock:
    artifacts = MagicMock()
    artifacts.delete_experiment_rows_if_table_exists = AsyncMock()
    return artifacts


@pytest.fixture
def mock_last_logged_service() -> MagicMock:
    last_logged = MagicMock()
    last_logged.delete_experiment_rows_if_table_exists = AsyncMock()
    return last_logged


def _projects(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> ProjectsService:
    return ProjectsService(
        mock_scalars_service, mock_artifacts_service, mock_last_logged_service
    )


@pytest.mark.asyncio
async def test_delete_experiment_data_runs_delete_mutations_when_tables_exist(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    out = await svc.delete_experiment_data(project_id, experiment_id)

    assert out.deleted is True
    mock_scalars_service.delete_experiment_rows_if_table_exists.assert_awaited_once_with(
        project_id, experiment_id
    )
    mock_artifacts_service.delete_experiment_rows_if_table_exists.assert_awaited_once_with(
        project_id, experiment_id
    )
    mock_last_logged_service.delete_experiment_rows_if_table_exists.assert_awaited_once_with(
        project_id, experiment_id
    )
    mock_scalars_service.compact_project_columns.assert_awaited_once_with(project_id)
    mock_scalars_service.invalidate_cache_for_experiment.assert_awaited_once_with(
        project_id, experiment_id
    )


@pytest.mark.asyncio
async def test_delete_experiment_data_skips_missing_tables_still_compacts(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    out = await svc.delete_experiment_data(project_id, experiment_id)

    assert out.deleted is True
    mock_scalars_service.compact_project_columns.assert_awaited_once_with(project_id)
    mock_scalars_service.invalidate_cache_for_experiment.assert_awaited_once_with(
        project_id, experiment_id
    )


@pytest.mark.asyncio
async def test_get_project_usage_marks_missing_tables(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    missing = ClickhouseTableUsageStats(
        table="t",
        exists=False,
        rows=0,
        columns=0,
        bytes=0,
    )
    mock_scalars_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=missing)
    mock_artifacts_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=missing)
    mock_last_logged_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=missing)
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    result = await svc.get_project_usage(project_id)

    assert result.project_id == project_id
    assert result.total_bytes == 0
    assert len(result.tables) == 3
    for row in result.tables:
        assert row.exists is False
        assert row.rows == 0
        assert row.columns == 0
        assert row.bytes == 0


@pytest.mark.asyncio
async def test_get_project_usage_counts_bytes_for_existing_tables(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    row = ClickhouseTableUsageStats(
        table="x",
        exists=True,
        rows=7,
        columns=4,
        bytes=50,
    )
    mock_scalars_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=row)
    mock_artifacts_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=row)
    mock_last_logged_service.get_clickhouse_table_usage_stats = AsyncMock(return_value=row)
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    result = await svc.get_project_usage(project_id)

    assert result.total_bytes == 150
    assert len(result.tables) == 3
    assert all(t.exists for t in result.tables)
    assert all(t.rows == 7 for t in result.tables)
    assert all(t.columns == 4 for t in result.tables)
    assert all(t.bytes == 50 for t in result.tables)


@pytest.mark.asyncio
async def test_get_experiment_usage_zero_when_scalars_table_missing(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    mock_scalars_service.get_clickhouse_table_usage_stats = AsyncMock(
        return_value=ClickhouseTableUsageStats(
            table="t", exists=False, rows=0, columns=0, bytes=0
        )
    )
    mock_artifacts_service.get_clickhouse_table_usage_stats = AsyncMock(
        return_value=ClickhouseTableUsageStats(
            table="t2", exists=False, rows=0, columns=0, bytes=0
        )
    )
    mock_last_logged_service.get_clickhouse_table_usage_stats = AsyncMock(
        return_value=ClickhouseTableUsageStats(
            table="t3", exists=False, rows=0, columns=0, bytes=0
        )
    )
    mock_scalars_service.get_experiment_usage_estimate = AsyncMock(
        return_value=ExperimentClickhouseUsageResponseDTO(
            project_id=project_id,
            experiment_id=experiment_id,
            rows=0,
            bytes=0,
        )
    )
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    result = await svc.get_experiment_usage(project_id, experiment_id)

    assert result.rows == 0
    assert result.bytes == 0
    assert result.experiment_id == experiment_id
    mock_scalars_service.get_experiment_usage_estimate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_experiment_usage_scales_bytes_by_row_fraction(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    client = AsyncMock()
    client.query = AsyncMock(
        side_effect=[
            MagicMock(result_rows=[[1]]),
            MagicMock(result_rows=[[10]]),
            MagicMock(result_rows=[[3]]),
        ]
    )
    real_scalars = ScalarsService(client, cache=None, last_logged_service=None)
    stats_three = [
        ClickhouseTableUsageStats(
            table=scalars_table,
            exists=True,
            rows=10,
            columns=4,
            bytes=100,
        ),
        ClickhouseTableUsageStats(table="a", exists=False, rows=0, columns=0, bytes=0),
        ClickhouseTableUsageStats(table="l", exists=False, rows=0, columns=0, bytes=0),
    ]
    result = await real_scalars.get_experiment_usage_estimate(
        project_id, experiment_id, stats_three
    )

    assert result.rows == 3
    assert result.bytes == 30


@pytest.mark.asyncio
async def test_list_storage_tables_returns_pagination(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    mock_scalars_service.list_admin_storage_tables = AsyncMock(
        return_value=ListStorageTablesResponseDTO(
            tables=[
                StorageTableRowDTO(name="scalars_abc", rows=10, bytes=100),
                StorageTableRowDTO(name="artifacts_info_def", rows=2, bytes=50),
            ],
            total=42,
            limit=10,
            offset=5,
        )
    )
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)

    result = await svc.list_storage_tables(q=None, limit=10, offset=5)

    assert result.total == 42
    assert result.limit == 10
    assert result.offset == 5
    assert len(result.tables) == 2
    assert result.tables[0].name == "scalars_abc"
    assert result.tables[0].rows == 10
    assert result.tables[0].bytes == 100
    mock_scalars_service.list_admin_storage_tables.assert_awaited_once_with(
        q=None, limit=10, offset=5
    )


@pytest.mark.asyncio
async def test_drop_table_rejects_bad_prefix(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)
    with pytest.raises(ValueError, match="managed"):
        await svc.drop_table("other_table")


@pytest.mark.asyncio
async def test_drop_table_rejects_non_alnum(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)
    with pytest.raises(ValueError, match="Invalid"):
        await svc.drop_table("scalars_x;x")


@pytest.mark.asyncio
async def test_drop_table_scalars_prefix_delegates(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    mock_scalars_service.drop_managed_table_by_name = AsyncMock()
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)
    out = await svc.drop_table("scalars_deadbeef0000")
    assert out.dropped is True
    assert out.table == "scalars_deadbeef0000"
    mock_scalars_service.drop_managed_table_by_name.assert_awaited_once_with(
        "scalars_deadbeef0000"
    )


@pytest.mark.asyncio
async def test_drop_table_artifacts_prefix_delegates(
    mock_scalars_service: MagicMock,
    mock_artifacts_service: MagicMock,
    mock_last_logged_service: MagicMock,
) -> None:
    mock_artifacts_service.drop_managed_table_by_name = AsyncMock()
    svc = _projects(mock_scalars_service, mock_artifacts_service, mock_last_logged_service)
    out = await svc.drop_table("artifacts_info_deadbeef0000")
    assert out.dropped is True
    mock_artifacts_service.drop_managed_table_by_name.assert_awaited_once_with(
        "artifacts_info_deadbeef0000"
    )
