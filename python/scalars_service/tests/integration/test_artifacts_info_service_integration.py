"""Integration scenarios for ``ArtifactsInfoService`` (artifacts_info ClickHouse table)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.artifacts_info.dto import (
    LogArtifactInfoRequestDTO,
    LogArtifactsInfoRequestDTO,
)
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore

from .helpers import domain_services, wait_for_clickhouse


@pytest.mark.asyncio
class TestArtifactsInfoServiceIntegration:
    async def test_create_log_get_delete_experiment_drop_table(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        name = await d.artifacts.create_clickhouse_table(project_id)
        assert name == SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)

        await d.artifacts.log_artifact_info(
            project_id,
            experiment_id,
            LogArtifactInfoRequestDTO(
                name="a1",
                artifact_type="image",
                path="hashaaa",
                step=0,
                metadata={"k": "v"},
                tags=["t"],
            ),
        )

        result = await d.artifacts.get_artifacts_info(
            project_id, experiment_id=experiment_id
        )
        assert result.total == 1
        assert result.data[0].experiment_id == experiment_id
        assert len(result.data[0].artifacts_info) == 1
        assert result.data[0].artifacts_info[0].name == "a1"

        await d.artifacts.delete_experiment_rows_if_table_exists(
            project_id, experiment_id
        )

        async def _artifacts_query_empty() -> bool:
            r = await d.artifacts.get_artifacts_info(
                project_id, experiment_id=experiment_id
            )
            return r.total == 0

        await wait_for_clickhouse(_artifacts_query_empty, err="artifacts delete not visible")

        empty = await d.artifacts.get_artifacts_info(
            project_id, experiment_id=experiment_id
        )
        assert empty.total == 0

        stats = await d.artifacts.get_clickhouse_table_usage_stats(project_id)
        assert stats.exists is True
        assert stats.rows == 0

        await d.artifacts.drop_clickhouse_table(project_id)

    async def test_log_batch_then_query_multiple_steps(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await d.artifacts.create_clickhouse_table(project_id)
        await d.artifacts.log_artifact_info_batch(
            project_id,
            experiment_id,
            LogArtifactsInfoRequestDTO(
                artifacts=[
                    LogArtifactInfoRequestDTO(
                        name="n0",
                        artifact_type="text",
                        path="p0",
                        step=0,
                    ),
                    LogArtifactInfoRequestDTO(
                        name="n1",
                        artifact_type="text",
                        path="p1",
                        step=1,
                    ),
                ]
            ),
        )

        result = await d.artifacts.get_artifacts_info(
            project_id, experiment_id=experiment_id, steps=[0, 1]
        )
        assert result.total == 1
        names = {a.name for a in result.data[0].artifacts_info}
        assert names == {"n0", "n1"}

        await d.artifacts.drop_clickhouse_table(project_id)

    async def test_delete_one_experiment_preserves_other_artifacts(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        e_keep = uuid4()
        e_drop = uuid4()

        await d.artifacts.create_clickhouse_table(project_id)
        await d.artifacts.log_artifact_info(
            project_id,
            e_keep,
            LogArtifactInfoRequestDTO(
                name="keep",
                artifact_type="image",
                path="h1",
                step=0,
            ),
        )
        await d.artifacts.log_artifact_info(
            project_id,
            e_drop,
            LogArtifactInfoRequestDTO(
                name="drop",
                artifact_type="image",
                path="h2",
                step=0,
            ),
        )

        all_rows = await d.artifacts.get_artifacts_info(project_id)
        assert all_rows.total == 2

        await d.artifacts.delete_experiment_rows_if_table_exists(project_id, e_drop)

        kept = await d.artifacts.get_artifacts_info(project_id, experiment_id=e_keep)
        dropped = await d.artifacts.get_artifacts_info(project_id, experiment_id=e_drop)
        assert kept.total == 1
        assert dropped.total == 0

        await d.artifacts.drop_clickhouse_table(project_id)

    async def test_drop_managed_table_by_name_after_create(
        self, integration_clickhouse_client
    ) -> None:
        d = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        await d.artifacts.create_clickhouse_table(project_id)
        table = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)

        await d.artifacts.drop_managed_table_by_name(table)
        stats = await d.artifacts.get_clickhouse_table_usage_stats(project_id)
        assert stats.exists is False
