"""Integration scenarios for ``LastLoggedService`` (per-project last_logged table)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.scalars.dto import LogScalarRequestDTO
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore

from .helpers import domain_services, wait_for_clickhouse


@pytest.mark.asyncio
class TestLastLoggedServiceIntegration:
    async def test_create_touch_query_delete_experiment_drop(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        table = await d.last_logged.create_clickhouse_table(project_id)
        assert table == SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)

        await d.last_logged.touch(project_id, experiment_id)

        page = await d.last_logged.get_last_logged_experiments(project_id)
        assert page.total == 1
        assert page.data[0].experiment_id == experiment_id

        await d.last_logged.delete_experiment_rows_if_table_exists(
            project_id, experiment_id
        )

        async def _last_logged_empty() -> bool:
            page = await d.last_logged.get_last_logged_experiments(project_id)
            return page.total == 0

        await wait_for_clickhouse(_last_logged_empty, err="last_logged delete not visible")

        await d.last_logged.drop_clickhouse_table(project_id)

    async def test_last_logged_tracks_two_experiments_then_delete_one(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        e1 = uuid4()
        e2 = uuid4()

        await d.projects.create_project_table(project_id)
        await d.scalars.log_scalar(
            project_id, e1, LogScalarRequestDTO(scalars={"x": 1.0}, step=0, tags=None)
        )
        await d.scalars.log_scalar(
            project_id, e2, LogScalarRequestDTO(scalars={"x": 2.0}, step=0, tags=None)
        )

        both = await d.last_logged.get_last_logged_experiments(project_id)
        assert both.total == 2
        ids = {row.experiment_id for row in both.data}
        assert ids == {e1, e2}

        filtered = await d.last_logged.get_last_logged_experiments(
            project_id, experiment_ids=[e1]
        )
        assert filtered.total == 1
        assert filtered.data[0].experiment_id == e1

        await d.last_logged.delete_experiment_rows_if_table_exists(project_id, e1)
        remaining = await d.last_logged.get_last_logged_experiments(project_id)
        assert remaining.total == 1
        assert remaining.data[0].experiment_id == e2

        await d.projects.delete_project_table(project_id)

    async def test_touch_updates_existing_row(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await d.last_logged.create_clickhouse_table(project_id)
        await d.last_logged.touch(project_id, experiment_id)
        first = await d.last_logged.get_last_logged_experiments(
            project_id, experiment_ids=[experiment_id]
        )
        t1 = first.data[0].last_modified

        await d.last_logged.touch(project_id, experiment_id)
        second = await d.last_logged.get_last_logged_experiments(
            project_id, experiment_ids=[experiment_id]
        )
        t2 = second.data[0].last_modified
        assert t2 >= t1

        await d.last_logged.drop_clickhouse_table(project_id)

    async def test_usage_stats_reflects_row_after_touch(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await d.last_logged.create_clickhouse_table(project_id)
        stats0 = await d.last_logged.get_clickhouse_table_usage_stats(project_id)
        assert stats0.rows == 0

        await d.last_logged.touch(project_id, experiment_id)
        stats1 = await d.last_logged.get_clickhouse_table_usage_stats(project_id)
        assert stats1.exists is True
        assert stats1.rows == 1

        await d.last_logged.drop_clickhouse_table(project_id)
