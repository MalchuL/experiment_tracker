import pytest
from uuid import UUID

from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS
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
    result = f"ALTER TABLE scalars_mapping_test DELETE WHERE project_id = '{project_id}'"
    assert SCALARS_DB_UTILS.build_delete_mapping_statement(project_id) == result


def test_validate_scalar_column_name():
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss_1") == "loss_1"
    assert (
        SCALARS_DB_UTILS.validate_scalar_column_name("  val loss\tstep  ")
        == "val_loss_step"
    )
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss/1") is None
    assert SCALARS_DB_UTILS.validate_scalar_column_name("   \n\t ") == "_empty_"
