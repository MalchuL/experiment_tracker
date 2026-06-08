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
    assert "ENGINE = ReplacingMergeTree(__timestamp__)" in ddl
    assert "ORDER BY (__experiment_id__, __name__, __step__, __artifact_type__)" in ddl
    assert "__artifact_type__ LowCardinality(String)" in ddl
    assert "__path__ String" in ddl


def test_build_select_artifacts_info_statement() -> None:
    project_id = uuid4()
    query = SCALARS_DB_UTILS.build_select_artifacts_info_statement(
        "artifacts_info_project",
        experiment_ids=[project_id],
        artifact_types=["image"],
        names=["predictions"],
        steps=[1, 2],
    )
    assert "FROM artifacts_info_project" in query
    assert "__artifact_type__ IN ('image')" in query
    assert "__name__ IN ('predictions')" in query
    assert "__step__ IN (1, 2)" in query


def test_build_select_artifacts_info_summary_statement() -> None:
    project_id = uuid4()
    query = SCALARS_DB_UTILS.build_select_artifacts_info_summary_statement(
        "artifacts_info_project",
        experiment_ids=[project_id],
        artifact_types=["image"],
        names=["predictions"],
        max_steps=25,
    )
    assert "FROM artifacts_info_project" in query
    assert "arraySort(groupUniqArray(__step__)) AS steps" in query
    assert "max(__timestamp__) AS last_modified" in query
    assert "range(toUInt32(25))" not in query
    assert "toInt64(24)" in query
    assert "GROUP BY __experiment_id__, __artifact_type__, __name__" in query
    assert "__artifact_type__ IN ('image')" in query
    assert "__name__ IN ('predictions')" in query


def test_build_artifact_experiment_page_statements_respect_filters() -> None:
    count_query = SCALARS_DB_UTILS.build_count_distinct_artifact_experiments_statement(
        "artifacts_info_project",
        artifact_types=["image"],
        names=["predictions"],
    )
    page_query = SCALARS_DB_UTILS.build_select_artifact_experiment_id_page_statement(
        "artifacts_info_project",
        artifact_types=["image"],
        names=["predictions"],
        limit=25,
        offset=50,
    )

    assert "uniqExact(__experiment_id__)" in count_query
    assert "__artifact_type__ IN ('image')" in count_query
    assert "__name__ IN ('predictions')" in count_query
    assert "GROUP BY __experiment_id__ ORDER BY __experiment_id__" in page_query
    assert "LIMIT 25 OFFSET 50" in page_query
