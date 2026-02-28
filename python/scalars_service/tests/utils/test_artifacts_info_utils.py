from uuid import uuid4

from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS


def test_safe_artifacts_info_table_name() -> None:
    project_id = uuid4()
    assert SCALARS_DB_UTILS.safe_artifacts_info_table_name(project_id).startswith(
        "artifacts_info_"
    )


def test_build_create_artifacts_info_table_statement() -> None:
    ddl = SCALARS_DB_UTILS.build_create_artifacts_info_table_statement(
        "artifacts_info_project"
    )
    assert "CREATE TABLE IF NOT EXISTS artifacts_info_project" in ddl
    assert "__artifact_type__ LowCardinality(String)" in ddl
    assert "__path__ String" in ddl


def test_build_select_artifacts_info_statement() -> None:
    project_id = uuid4()
    query = SCALARS_DB_UTILS.build_select_artifacts_info_statement(
        "artifacts_info_project",
        experiment_ids=[project_id],
        artifact_types=["image"],
        names=["predictions"],
    )
    assert "FROM artifacts_info_project" in query
    assert "__artifact_type__ IN ('image')" in query
    assert "__name__ IN ('predictions')" in query
