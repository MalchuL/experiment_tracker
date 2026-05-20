from datetime import datetime

import pytest
from uuid import UUID

from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS
from app.domain.utils.scalars_select_sql import SCALARS_SELECT_SQL
from config import get_settings  # type: ignore


def test_build_create_table_statement():
    result = (
        "CREATE TABLE IF NOT EXISTS scalars_123 "
        "(__timestamp__ DateTime64(3), __experiment_id__ UUID, __step__ Int64, __tags__ Array(String)) "
        "ENGINE = MergeTree() PARTITION BY toDate(__timestamp__) ORDER BY (__experiment_id__, __step__)"
    )
    assert (
        SCALARS_DB_UTILS.build_create_scalars_table_statement("scalars_123") == result
    )


def test_build_create_table_statement_with_scalars():
    result = (
        "CREATE TABLE IF NOT EXISTS scalars_123 "
        "(__timestamp__ DateTime64(3), __experiment_id__ UUID, __step__ Int64, __tags__ Array(String), "
        "loss Nullable(Float64), acc Nullable(Float64)) "
        "ENGINE = MergeTree() PARTITION BY toDate(__timestamp__) ORDER BY (__experiment_id__, __step__)"
    )
    assert (
        SCALARS_DB_UTILS.build_create_scalars_table_statement(
            "scalars_123", ["loss", "acc"]
        )
        == result
    )


def test_remove_table():
    result = "DROP TABLE IF EXISTS scalars_123"
    assert SCALARS_DB_UTILS.build_drop_table_statement("scalars_123") == result


def test_build_alter_delete_experiment_rows_statement():
    exp = UUID("33333333-3333-3333-3333-333333333333")
    sql = SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
        "scalars_abcd",
        exp,
        "__experiment_id__",
    )
    assert sql == (
        "ALTER TABLE scalars_abcd DELETE WHERE __experiment_id__ = " f"'{exp}'"
    )
    sql_last = SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
        "scalars_last_logged_abcd",
        exp,
        "experiment_id",
    )
    assert "DELETE WHERE experiment_id =" in sql_last


def test_build_alter_delete_experiment_rows_rejects_unknown_column():
    with pytest.raises(ValueError, match="experiment_id_column"):
        SCALARS_DB_UTILS.build_alter_delete_experiment_rows_statement(
            "scalars_x",
            UUID("44444444-4444-4444-4444-444444444444"),
            "malicious",
        )


def test_build_alter_table_drop_column_if_exists_statement():
    assert (
        SCALARS_DB_UTILS.build_alter_table_drop_column_if_exists_statement(
            "scalars_abcd", "loss_metric"
        )
        == "ALTER TABLE scalars_abcd DROP COLUMN IF EXISTS loss_metric"
    )


def test_safe_scalars_table_name():
    project_id = UUID("00000000-0000-0000-0000-000000000123")
    result = "scalars_00000000000000000000000000000123"
    assert SCALARS_DB_UTILS.safe_scalars_table_name(project_id) == result


def test_incorrect_safe_scalars_table_name():
    with pytest.raises(AttributeError):
        SCALARS_DB_UTILS.safe_scalars_table_name("not-a-uuid")  # type: ignore[arg-type]


def test_select_statement():
    exp1 = UUID("11111111-1111-1111-1111-111111111111")
    exp2 = UUID("22222222-2222-2222-2222-222222222222")
    result = (
        "SELECT __timestamp__, __experiment_id__, __step__, __tags__, loss, acc FROM scalars_123 "
        f"WHERE __experiment_id__ IN ('{exp1}', '{exp2}') ORDER BY __experiment_id__, __step__"
    )
    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123",
            scalar_columns=["loss", "acc"],
            experiment_ids=[exp1, exp2],
        )
        == result
    )


def test_select_uniform_sampled_column_non_null_and_windows():
    exp1 = UUID("11111111-1111-1111-1111-111111111111")
    sql = SCALARS_DB_UTILS.build_select_uniform_sampled_column(
        "scalars_123",
        "loss",
        [exp1],
        max_points=50,
    )
    assert "loss IS NOT NULL" in sql
    assert "SELECT * EXCEPT(_u_rn, _u_cnt) FROM (" in sql
    assert (
        "row_number() OVER (PARTITION BY __experiment_id__ ORDER BY __step__, __timestamp__)"
        in sql
    )
    assert "count(*) OVER (PARTITION BY __experiment_id__)" in sql
    assert "arrayExists(" not in sql
    assert "range(toUInt32(50))" not in sql
    assert "toInt64(49)" in sql


def test_alter_table_add_columns_statement():
    result = (
        "ALTER TABLE scalars_123 "
        "ADD COLUMN IF NOT EXISTS loss Nullable(Float64), "
        "ADD COLUMN IF NOT EXISTS acc Nullable(Float64)"
    )
    assert (
        SCALARS_DB_UTILS.build_alter_table_add_columns_statement(
            "scalars_123", ["loss", "acc"]
        )
        == result
    )


def test_table_existence_statement():
    result = (
        "SELECT count() > 0 FROM system.tables "
        "WHERE database = currentDatabase() AND name = 'scalars_123'"
    )
    assert SCALARS_DB_UTILS.build_table_existence_statement("scalars_123") == result


def test_create_mapping_table_statement(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCALARS_MAPPING_TABLE", "scalars_mapping_test")
    get_settings.cache_clear()
    result = (
        "CREATE TABLE IF NOT EXISTS scalars_mapping_test "
        "(project_id UUID, mapping Map(String, String), updated_at DateTime64(3)) "
        "ENGINE = ReplacingMergeTree(updated_at) ORDER BY project_id"
    )
    assert SCALARS_DB_UTILS.build_create_mapping_table_statement() == result


def test_select_mapping_statement(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCALARS_MAPPING_TABLE", "scalars_mapping_test")
    get_settings.cache_clear()
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    result = (
        "SELECT mapping FROM scalars_mapping_test "
        f"WHERE project_id = '{project_id}' ORDER BY updated_at DESC LIMIT 1"
    )
    assert SCALARS_DB_UTILS.build_select_mapping_statement(project_id) == result


def test_delete_mapping_statement(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCALARS_MAPPING_TABLE", "scalars_mapping_test")
    get_settings.cache_clear()
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    result = (
        f"ALTER TABLE scalars_mapping_test DELETE WHERE project_id = '{project_id}'"
    )
    assert SCALARS_DB_UTILS.build_delete_mapping_statement(project_id) == result


def test_validate_scalar_column_name():
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss_1") == "loss_1"
    assert (
        SCALARS_DB_UTILS.validate_scalar_column_name("  val loss\tstep  ")
        == "val_loss_step"
    )
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss/1") is None
    assert SCALARS_DB_UTILS.validate_scalar_column_name("   \n\t ") == "_empty_"


def test_scalars_select_sql_usage_and_admin_queries():
    assert SCALARS_SELECT_SQL.count_all_rows("scalars_abcd1234") == (
        "SELECT count() FROM scalars_abcd1234"
    )

    exp = UUID("22222222-2222-2222-2222-222222222222")
    assert SCALARS_SELECT_SQL.count_rows_for_experiment(
        "scalars_abcd1234", "__experiment_id__", str(exp)
    ) == ("SELECT count() FROM scalars_abcd1234 " f"WHERE __experiment_id__ = '{exp}'")

    assert SCALARS_SELECT_SQL.managed_tables_predicate_sql() == (
        "database = currentDatabase() "
        "AND (name LIKE 'scalars_%' OR name LIKE 'artifacts_info_%')"
    )

    extra = " AND positionCaseInsensitive(name, 'x') > 0"
    assert "system.tables" in SCALARS_SELECT_SQL.list_tables_count(extra)
    assert extra in SCALARS_SELECT_SQL.list_tables_count(extra)

    page_sql = SCALARS_SELECT_SQL.list_tables_page(
        extra_predicate=extra, limit=10, offset=5
    )
    assert "LIMIT 10 OFFSET 5" in page_sql
    assert "total_rows" in page_sql


def test_datetime_sql_literals_use_utc_timezone():
    """toDateTime64 from formatted strings must parse as UTC (matches naive UTC writes)."""
    ts = datetime(2024, 6, 15, 10, 20, 30, 456000)
    exp = UUID("33333333-3333-3333-3333-333333333333")
    upsert = SCALARS_DB_UTILS.build_upsert_last_logged_statement(
        "last_logged_x", exp, ts
    )
    assert "toDateTime64('2024-06-15 10:20:30.456', 3, 'UTC')" in upsert

    wide = SCALARS_DB_UTILS.build_select_statement(
        "scalars_t",
        scalar_columns=["loss"],
        experiment_ids=[exp],
        start_time=ts,
        end_time=ts,
    )
    assert "toDateTime64('2024-06-15 10:20:30.456', 3, 'UTC')" in wide

    artifacts = SCALARS_DB_UTILS.build_select_artifacts_info_statement(
        "artifacts_info_t",
        experiment_ids=[exp],
        start_time=ts,
        end_time=ts,
    )
    assert "toDateTime64('2024-06-15 10:20:30.456', 3, 'UTC')" in artifacts
