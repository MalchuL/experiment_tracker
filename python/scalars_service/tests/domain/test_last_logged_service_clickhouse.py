"""Unit tests for ``LastLoggedService`` ClickHouse table lifecycle helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.last_logged.service import LastLoggedService
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore


@pytest.fixture
def project_id():
    return uuid4()


@pytest.fixture
def experiment_id():
    return uuid4()


def _svc(client: AsyncMock) -> LastLoggedService:
    return LastLoggedService(client)


@pytest.mark.asyncio
async def test_create_clickhouse_table_issues_ddl(project_id) -> None:
    client = AsyncMock()
    svc = _svc(client)

    name = await svc.create_clickhouse_table(project_id)

    assert name == SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
    client.command.assert_awaited_once()
    assert "CREATE TABLE" in client.command.await_args.args[0]
    assert name in client.command.await_args.args[0]


@pytest.mark.asyncio
async def test_drop_clickhouse_table_issues_drop(project_id) -> None:
    client = AsyncMock()
    svc = _svc(client)

    await svc.drop_clickhouse_table(project_id)

    expected = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
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
    assert stats.table == SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)


@pytest.mark.asyncio
async def test_get_clickhouse_table_usage_stats_when_present(project_id) -> None:
    table = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
    client = AsyncMock()
    client.query = AsyncMock(
        side_effect=[
            MagicMock(result_rows=[[1]]),
            MagicMock(result_rows=[[5]]),
            MagicMock(result_rows=[("experiment_id",), ("last_modified",)]),
            MagicMock(result_rows=[[16]]),
        ]
    )
    svc = _svc(client)

    stats = await svc.get_clickhouse_table_usage_stats(project_id)

    assert stats.table == table
    assert stats.exists is True
    assert stats.rows == 5
    assert stats.columns == 2
    assert stats.bytes == 16
