from uuid import uuid4

from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS


def test_safe_objects_table_name() -> None:
    project_id = uuid4()
    assert SCALARS_DB_UTILS.safe_objects_table_name(project_id).startswith("objects_")


def test_build_create_objects_table_statement() -> None:
    ddl = SCALARS_DB_UTILS.build_create_objects_table_statement("objects_project")
    assert "CREATE TABLE IF NOT EXISTS objects_project" in ddl
    assert "__object_type__ LowCardinality(String)" in ddl
    assert "__path__ String" in ddl


def test_build_select_objects_statement() -> None:
    project_id = uuid4()
    query = SCALARS_DB_UTILS.build_select_objects_statement(
        "objects_project",
        experiment_ids=[project_id],
        object_types=["image"],
        names=["predictions"],
    )
    assert "FROM objects_project" in query
    assert "__object_type__ IN ('image')" in query
    assert "__name__ IN ('predictions')" in query
