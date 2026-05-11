"""Unit tests for ``ScalarsService`` ClickHouse project-table helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.projects.dto import ClickhouseTableUsageStats
from app.domain.scalars.service import ScalarsService
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore


@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def experiment_id():
    return uuid4()


def _svc(client: AsyncMock) -> ScalarsService:
    return ScalarsService(client, cache=None, last_logged_service=None)


@pytest.mark.asyncio
async def test_create_clickhouse_table_issues_ddl_and_returns_table_name(
    project_id,
) -> None:
    client = AsyncMock()
    svc = _svc(client)

    name = await svc.create_clickhouse_table(project_id)

    assert name == SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    client.command.assert_awaited_once()
    ddl = client.command.await_args.args[0]
    assert "CREATE TABLE" in ddl
    assert name in ddl


@pytest.mark.asyncio
async def test_get_scalars_table_existence_reflects_query(project_id) -> None:
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[1]]))
    svc = _svc(client)

    table_name, exists = await svc.get_scalars_table_existence(project_id)

    assert table_name == SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    assert exists is True
    client.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_experiment_ids_for_project_maps_rows(project_id) -> None:
    e1, e2 = uuid4(), uuid4()
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[e1], [e2]]))
    svc = _svc(client)

    out = await svc.list_experiment_ids_for_project(project_id)

    assert out == [{"experiment_id": e1}, {"experiment_id": e2}]


@pytest.mark.asyncio
async def test_delete_scalar_mapping_for_project_runs_delete(project_id) -> None:
    client = AsyncMock()
    svc = _svc(client)

    await svc.delete_scalar_mapping_for_project(project_id)

    client.command.assert_awaited_once()
    sql = client.command.await_args.args[0]
    assert str(project_id) in sql or "project_id" in sql.lower()


@pytest.mark.asyncio
async def test_drop_clickhouse_table_issues_drop(project_id) -> None:
    client = AsyncMock()
    svc = _svc(client)

    name = await svc.drop_clickhouse_table(project_id)

    expected = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    assert name == expected
    client.command.assert_awaited_once()
    assert expected in client.command.await_args.args[0]


@pytest.mark.asyncio
async def test_delete_experiment_rows_skips_when_table_missing(
    project_id, experiment_id
) -> None:
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[0]]))
    svc = _svc(client)

    await svc.delete_experiment_rows_if_table_exists(project_id, experiment_id)

    client.command.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_experiment_rows_runs_alter_when_table_present(
    project_id, experiment_id
) -> None:
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[1]]))
    svc = _svc(client)

    await svc.delete_experiment_rows_if_table_exists(project_id, experiment_id)

    client.command.assert_awaited_once()
    assert "DELETE" in client.command.await_args.args[0].upper()


@pytest.mark.asyncio
async def test_get_clickhouse_table_usage_stats_when_missing(project_id) -> None:
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[0]]))
    svc = _svc(client)

    stats = await svc.get_clickhouse_table_usage_stats(project_id)

    assert stats.exists is False
    assert stats.rows == 0
    assert stats.bytes == 0
    assert stats.table == SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    assert client.query.await_count == 1


@pytest.mark.asyncio
async def test_get_clickhouse_table_usage_stats_when_present(project_id) -> None:
    table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    exists = MagicMock(result_rows=[[1]])
    count_row = MagicMock(result_rows=[[12]])
    describe = MagicMock(result_rows=[("a",), ("b",)])
    bytes_row = MagicMock(result_rows=[[99]])
    client = AsyncMock()
    client.query = AsyncMock(side_effect=[exists, count_row, describe, bytes_row])
    svc = _svc(client)

    stats = await svc.get_clickhouse_table_usage_stats(project_id)

    assert stats.table == table
    assert stats.exists is True
    assert stats.rows == 12
    assert stats.columns == 2
    assert stats.bytes == 99


@pytest.mark.asyncio
async def test_get_experiment_usage_estimate_when_scalars_missing(
    project_id, experiment_id
) -> None:
    client = AsyncMock()
    client.query = AsyncMock(return_value=MagicMock(result_rows=[[0]]))
    svc = _svc(client)

    out = await svc.get_experiment_usage_estimate(
        project_id, experiment_id, ()
    )

    assert out.rows == 0
    assert out.bytes == 0
    assert out.experiment_id == experiment_id


@pytest.mark.asyncio
async def test_get_experiment_usage_estimate_scales_bytes(
    project_id, experiment_id
) -> None:
    scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
    client = AsyncMock()
    client.query = AsyncMock(
        side_effect=[
            MagicMock(result_rows=[[1]]),
            MagicMock(result_rows=[[8]]),
            MagicMock(result_rows=[[2]]),
        ]
    )
    svc = _svc(client)
    project_stats = [
        ClickhouseTableUsageStats(
            table=scalars_table,
            exists=True,
            rows=8,
            columns=3,
            bytes=80,
        )
    ]

    out = await svc.get_experiment_usage_estimate(
        project_id, experiment_id, project_stats
    )

    assert out.rows == 2
    assert out.bytes == 20


@pytest.mark.asyncio
async def test_list_admin_storage_tables_clamps_limit_and_passes_offset() -> None:
    client = AsyncMock()
    client.query = AsyncMock(
        side_effect=[
            MagicMock(result_rows=[[5]]),
            MagicMock(result_rows=[("scalars_x", 1, 2)]),
        ]
    )
    svc = _svc(client)

    out = await svc.list_admin_storage_tables(q=None, limit=500, offset=3)

    assert out.limit == 200
    assert out.offset == 3
    assert out.total == 5
    page_call = client.query.await_args_list[1]
    assert "LIMIT 200" in page_call.args[0] or "limit 200" in page_call.args[0].lower()


@pytest.mark.asyncio
async def test_list_admin_storage_tables_sanitizes_search_q() -> None:
    client = AsyncMock()
    client.query = AsyncMock(
        side_effect=[
            MagicMock(result_rows=[[0]]),
            MagicMock(result_rows=[]),
        ]
    )
    svc = _svc(client)

    await svc.list_admin_storage_tables(q="foo'; DROP--", limit=10, offset=0)

    count_sql = client.query.await_args_list[0].args[0]
    assert "foo'; DROP" not in count_sql
    assert "positionCaseInsensitive" in count_sql
    assert "fooDROP--" in count_sql


@pytest.mark.asyncio
async def test_drop_managed_table_by_name_rejects_bad_prefix() -> None:
    client = AsyncMock()
    svc = _svc(client)
    with pytest.raises(ValueError, match="managed"):
        await svc.drop_managed_table_by_name("artifacts_info_x")


@pytest.mark.asyncio
async def test_drop_managed_table_by_name_rejects_invalid_chars() -> None:
    client = AsyncMock()
    svc = _svc(client)
    with pytest.raises(ValueError, match="Invalid"):
        await svc.drop_managed_table_by_name("scalars_bad;name")


@pytest.mark.asyncio
async def test_drop_managed_table_by_name_issues_drop() -> None:
    client = AsyncMock()
    svc = _svc(client)
    await svc.drop_managed_table_by_name("scalars_abcd0000")
    client.command.assert_awaited_once()
    assert "scalars_abcd0000" in client.command.await_args.args[0]
