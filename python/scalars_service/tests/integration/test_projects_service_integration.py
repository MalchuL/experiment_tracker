"""Integration scenarios for ``ProjectsService`` (orchestration over real ClickHouse)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.artifacts_info.dto import LogArtifactInfoRequestDTO
from app.domain.scalars.dto import LogScalarRequestDTO
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS  # type: ignore

from .helpers import domain_services, wait_for_clickhouse


@pytest.mark.asyncio
class TestProjectsServiceIntegration:
    async def test_create_get_existence_usage_list_experiments_delete_project(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()

        created = await svc.projects.create_project_table(project_id)
        assert created.table_name == SCALARS_DB_UTILS.safe_scalars_table_name(project_id)

        existence = await svc.projects.get_project_table_existence(project_id)
        assert existence.exists is True

        usage = await svc.projects.get_project_usage(project_id)
        assert usage.project_id == project_id
        assert len(usage.tables) == 3
        assert all(t.exists for t in usage.tables)
        names = {t.table for t in usage.tables}
        assert SCALARS_DB_UTILS.safe_scalars_table_name(project_id) in names
        assert SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id) in names
        assert SCALARS_DB_UTILS.safe_last_logged_table_name(project_id) in names

        experiments = await svc.projects.get_project_experiments_ids(project_id)
        assert experiments == []

        deleted = await svc.projects.delete_project_table(project_id)
        assert "deleted" in deleted.message.lower()

        after = await svc.projects.get_project_table_existence(project_id)
        assert after.exists is False

    async def test_delete_experiment_data_clears_scalars_and_artifacts_and_last_logged(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await svc.projects.create_project_table(project_id)
        await svc.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"loss": 1.0}, step=1, tags=None),
        )
        await svc.artifacts.log_artifact_info(
            project_id,
            experiment_id,
            LogArtifactInfoRequestDTO(
                name="img",
                artifact_type="image",
                path="deadbeef",
                step=1,
                metadata=None,
                tags=None,
            ),
        )

        usage_before = await svc.projects.get_project_usage(project_id)
        scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        artifacts_table = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
        last_table = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
        by_name = {t.table: t for t in usage_before.tables}
        assert by_name[scalars_table].rows >= 1
        assert by_name[artifacts_table].rows >= 1
        assert by_name[last_table].rows >= 1

        exp_usage_before = await svc.projects.get_experiment_usage(
            project_id, experiment_id
        )
        assert exp_usage_before.rows >= 1

        await svc.projects.delete_experiment_data(project_id, experiment_id)

        async def _usage_cleared() -> bool:
            u = await svc.projects.get_project_usage(project_id)
            scalars_table = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
            artifacts_table = SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id)
            last_table = SCALARS_DB_UTILS.safe_last_logged_table_name(project_id)
            by = {t.table: t for t in u.tables}
            return (
                by[scalars_table].rows == 0
                and by[artifacts_table].rows == 0
                and by[last_table].rows == 0
            )

        await wait_for_clickhouse(_usage_cleared, err="project-wide delete not visible")

        usage_after = await svc.projects.get_project_usage(project_id)
        by_name_after = {t.table: t for t in usage_after.tables}
        assert by_name_after[scalars_table].rows == 0
        assert by_name_after[artifacts_table].rows == 0
        assert by_name_after[last_table].rows == 0

        exp_usage_after = await svc.projects.get_experiment_usage(
            project_id, experiment_id
        )
        assert exp_usage_after.rows == 0

        artifacts_view = await svc.artifacts.get_artifacts_info(
            project_id, experiment_id=experiment_id
        )
        assert artifacts_view.total == 0

        await svc.projects.delete_project_table(project_id)

    async def test_delete_one_experiment_preserves_other_in_lists_and_usage(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        e_keep = uuid4()
        e_drop = uuid4()

        await svc.projects.create_project_table(project_id)
        await svc.scalars.log_scalar(
            project_id,
            e_keep,
            LogScalarRequestDTO(scalars={"a": 1.0}, step=0, tags=None),
        )
        await svc.scalars.log_scalar(
            project_id,
            e_drop,
            LogScalarRequestDTO(scalars={"b": 2.0}, step=0, tags=None),
        )

        ids_before = await svc.projects.get_project_experiments_ids(project_id)
        id_set = {row["experiment_id"] for row in ids_before}
        assert id_set == {e_keep, e_drop}

        await svc.projects.delete_experiment_data(project_id, e_drop)

        ids_after = await svc.projects.get_project_experiments_ids(project_id)
        assert {row["experiment_id"] for row in ids_after} == {e_keep}

        assert (await svc.projects.get_experiment_usage(project_id, e_drop)).rows == 0
        assert (await svc.projects.get_experiment_usage(project_id, e_keep)).rows >= 1

        await svc.projects.delete_project_table(project_id)

    async def test_delete_experiment_data_is_idempotent(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await svc.projects.create_project_table(project_id)
        await svc.projects.delete_experiment_data(project_id, experiment_id)
        await svc.projects.delete_experiment_data(project_id, experiment_id)

        usage = await svc.projects.get_project_usage(project_id)
        assert all(t.rows == 0 for t in usage.tables)

        await svc.projects.delete_project_table(project_id)

    async def test_project_usage_bytes_non_decreasing_after_logs(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        experiment_id = uuid4()

        await svc.projects.create_project_table(project_id)
        usage0 = await svc.projects.get_project_usage(project_id)
        bytes0 = usage0.total_bytes

        await svc.scalars.log_scalar(
            project_id,
            experiment_id,
            LogScalarRequestDTO(scalars={"m": 0.5}, step=0, tags=None),
        )
        usage1 = await svc.projects.get_project_usage(project_id)
        assert usage1.total_bytes >= bytes0

        await svc.projects.delete_project_table(project_id)

    async def test_list_storage_tables_and_drop_managed_scalar_table(
        self, integration_clickhouse_client
    ) -> None:
        svc = domain_services(integration_clickhouse_client)
        project_id = uuid4()
        scalars_name = SCALARS_DB_UTILS.safe_scalars_table_name(project_id)
        needle = project_id.hex[:12]

        await svc.projects.create_project_table(project_id)

        listing = await svc.projects.list_storage_tables(q=needle, limit=50, offset=0)
        assert listing.total >= 1
        assert scalars_name in {t.name for t in listing.tables}

        await svc.projects.drop_table(scalars_name)
        existence = await svc.projects.get_project_table_existence(project_id)
        assert existence.exists is False

        await svc.last_logged.drop_clickhouse_table(project_id)
        await svc.artifacts.drop_clickhouse_table(project_id)
        await svc.scalars.delete_scalar_mapping_for_project(project_id)
