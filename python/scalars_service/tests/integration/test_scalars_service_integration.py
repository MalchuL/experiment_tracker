"""Integration scenarios for ``ScalarsService`` ClickHouse helpers and logging."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.scalars.dto import LogScalarRequestDTO
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore

from .helpers import domain_services, wait_for_clickhouse


@pytest.mark.asyncio
class TestScalarsServiceIntegration:
    async def test_ch_table_create_existence_log_steps_usage_delete_rows_compact_drop(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        table = await d.scalars.create_clickhouse_table(project_id)
        name, exists = await d.scalars.get_scalars_table_existence(project_id)
        assert name == table
        assert exists is True

        await d.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"x": 1.0}, step=0, tags=None),
        )
        await d.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"x": 2.0}, step=1, tags=None),
        )

        stats = await d.scalars.get_clickhouse_table_usage_stats(project_id)
        assert stats.exists is True
        assert stats.rows >= 2

        ids = await d.scalars.list_experiment_ids_for_project(project_id)
        assert {r["experiment_id"] for r in ids} == {experiment_id}

        await d.scalars.delete_experiment_rows_if_table_exists(project_id, experiment_id)

        async def _scalars_row_count_zero() -> bool:
            s = await d.scalars.get_clickhouse_table_usage_stats(project_id)
            return s.rows == 0

        await wait_for_clickhouse(_scalars_row_count_zero, err="scalars delete mutation not visible")

        compact = await d.scalars.compact_project_columns(project_id)
        assert compact.dropped_columns is not None

        await d.scalars.drop_clickhouse_table(project_id)
        _, exists_after = await d.scalars.get_scalars_table_existence(project_id)
        assert exists_after is False

    async def test_distinct_scalar_columns_increase_with_second_metric_name(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await d.scalars.create_clickhouse_table(project_id)
        await d.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"alpha": 1.0}, step=0, tags=None),
        )
        cols_after_one = (
            await d.scalars.get_clickhouse_table_usage_stats(project_id)
        ).columns
        await d.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"beta": 2.0}, step=0, tags=None),
        )
        cols_after_two = (
            await d.scalars.get_clickhouse_table_usage_stats(project_id)
        ).columns
        assert cols_after_two > cols_after_one

        await d.scalars.delete_experiment_rows_if_table_exists(project_id, experiment_id)
        await d.scalars.drop_clickhouse_table(project_id)
        await d.scalars.delete_scalar_mapping_for_project(project_id)

    async def test_list_admin_storage_tables_filter_and_limit_clamp(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        await d.scalars.create_clickhouse_table(project_id)
        needle = project_id.hex[:10]

        page = await d.scalars.list_admin_storage_tables(q=needle, limit=999, offset=0)
        assert page.limit == 200
        assert page.offset == 0
        assert page.total >= 1

        await d.scalars.drop_clickhouse_table(project_id)
        await d.scalars.delete_scalar_mapping_for_project(project_id)

    async def test_drop_managed_table_by_name_round_trip(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        await d.scalars.create_clickhouse_table(project_id)
        name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)

        await d.scalars.drop_managed_table_by_name(name)
        _, exists = await d.scalars.get_scalars_table_existence(project_id)
        assert exists is False

        await d.scalars.delete_scalar_mapping_for_project(project_id)

    async def test_get_experiment_usage_estimate_matches_row_share(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        e1 = uuid4()
        e2 = uuid4()

        await d.scalars.create_clickhouse_table(project_id)
        await d.scalars.log_scalar(
            project_id, e1, LogScalarRequestDTO(scalars={"u": 1.0}, step=0, tags=None)
        )
        await d.scalars.log_scalar(
            project_id, e1, LogScalarRequestDTO(scalars={"u": 1.0}, step=1, tags=None)
        )
        await d.scalars.log_scalar(
            project_id, e2, LogScalarRequestDTO(scalars={"u": 1.0}, step=0, tags=None)
        )

        project_usage = await d.projects.get_project_usage(project_id)
        out = await d.scalars.get_experiment_usage_estimate(
            project_id, e1, project_usage
        )
        assert out.rows == 2
        scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        table_bytes = next(
            t.bytes for t in project_usage.tables if t.table == scalars_table
        )
        expected = int(table_bytes * (2 / 3))
        assert abs(out.bytes - expected) <= 1

        await d.scalars.delete_experiment_rows_if_table_exists(project_id, e1)
        await d.scalars.delete_experiment_rows_if_table_exists(project_id, e2)
        await d.scalars.drop_clickhouse_table(project_id)
        await d.scalars.delete_scalar_mapping_for_project(project_id)
