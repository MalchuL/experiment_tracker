import pytest
from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS


def test_build_create_table_statement():
    result = (
        "CREATE TABLE IF NOT EXISTS scalars_123 "
        "(__timestamp__ DateTime64(3), __experiment_id__ String, __step__ Int64, __tags__ Array(String)) "
        "ENGINE = MergeTree() PARTITION BY toDate(__timestamp__) ORDER BY (__experiment_id__, __step__)"
    )
    assert SCALARS_DB_UTILS.build_create_table_statement("scalars_123") == result


def test_build_create_table_statement_with_scalars():
    result = (
        "CREATE TABLE IF NOT EXISTS scalars_123 "
        "(__timestamp__ DateTime64(3), __experiment_id__ String, __step__ Int64, __tags__ Array(String), "
        "loss Nullable(Float64), acc Nullable(Float64)) "
        "ENGINE = MergeTree() PARTITION BY toDate(__timestamp__) ORDER BY (__experiment_id__, __step__)"
    )
    assert (
        SCALARS_DB_UTILS.build_create_table_statement("scalars_123", ["loss", "acc"])
        == result
    )


def test_remove_table():
    result = "DROP TABLE IF EXISTS scalars_123"
    assert SCALARS_DB_UTILS.build_drop_table_statement("scalars_123") == result


def test_safe_scalars_table_name():
    result = "scalars_123"
    assert SCALARS_DB_UTILS.safe_scalars_table_name("123") == result


def test_incorrect_safe_scalars_table_name():
    with pytest.raises(ValueError):
        SCALARS_DB_UTILS.safe_scalars_table_name("123" * 64)
    with pytest.raises(ValueError):
        SCALARS_DB_UTILS.safe_scalars_table_name("DROP TABLE scalars_123")


def test_select_statement():
    result = (
        "SELECT __timestamp__, __experiment_id__, __step__, __tags__, loss, acc FROM scalars_123 "
        "WHERE __experiment_id__ IN ('exp1', 'exp2') ORDER BY __experiment_id__, __step__"
    )
    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123",
            scalar_columns=["loss", "acc"],
            experiment_ids=["exp1", "exp2"],
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


def test_validate_scalar_column_name():
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss_1") == "loss_1"
    assert (
        SCALARS_DB_UTILS.validate_scalar_column_name("  val loss\tstep  ")
        == "val_loss_step"
    )
    assert SCALARS_DB_UTILS.validate_scalar_column_name("loss/1") == "loss/1"
    assert SCALARS_DB_UTILS.validate_scalar_column_name("   \n\t ") == "_empty_"
