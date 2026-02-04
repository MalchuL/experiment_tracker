from app.domain.utils.scalars_db_utils import SCALARS_DB_UTILS, ProjectTableColumns
import pytest


def test_build_create_table_statement():
    result = "CREATE TABLE scalars_123 (timestamp TIMESTAMP NOT NULL, experiment_id SYMBOL, scalar_name SYMBOL, value DOUBLE NOT NULL, step INT, tags STRING) TIMESTAMP(timestamp) PARTITION BY DAY"
    assert SCALARS_DB_UTILS.build_create_table_statement("scalars_123") == result


def test_remove_table():
    result = "DROP TABLE scalars_123"
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
    result = "SELECT timestamp, experiment_id, scalar_name, value, step, tags FROM scalars_123"
    assert SCALARS_DB_UTILS.build_select_statement("scalars_123") == result
    result = "SELECT timestamp, experiment_id, scalar_name, value, step, tags FROM scalars_123"
    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123",
            ["timestamp", "experiment_id", "scalar_name", "value", "step", "tags"],
        )
        == result
    )
    result = "SELECT timestamp, experiment_id, scalar_name, value, step, tags FROM scalars_123"
    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123",
            [
                ProjectTableColumns.TIMESTAMP,
                ProjectTableColumns.EXPERIMENT_ID,
                ProjectTableColumns.SCALAR_NAME,
                ProjectTableColumns.VALUE,
                ProjectTableColumns.STEP,
                ProjectTableColumns.TAGS,
            ],
        )
        == result
    )

    result = "SELECT experiment_id, scalar_name, value, step FROM scalars_123"
    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123",
            [
                ProjectTableColumns.EXPERIMENT_ID,
                ProjectTableColumns.SCALAR_NAME,
                ProjectTableColumns.VALUE,
                ProjectTableColumns.STEP,
            ],
        )
        == result
    )

    assert (
        SCALARS_DB_UTILS.build_select_statement(
            "scalars_123", ["experiment_id", "scalar_name", "value", "step"]
        )
        == result
    )


def test_insert_statement():
    result = "INSERT INTO scalars_123 (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)"
    assert SCALARS_DB_UTILS.build_insert_statement("scalars_123") == result
    result = "INSERT INTO scalars_123 (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)"
    assert (
        SCALARS_DB_UTILS.build_insert_statement(
            "scalars_123",
            ["timestamp", "experiment_id", "scalar_name", "value", "step", "tags"],
        )
        == result
    )
    result = "INSERT INTO scalars_123 (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)"
    assert (
        SCALARS_DB_UTILS.build_insert_statement(
            "scalars_123",
            [
                ProjectTableColumns.TIMESTAMP,
                ProjectTableColumns.EXPERIMENT_ID,
                ProjectTableColumns.SCALAR_NAME,
                ProjectTableColumns.VALUE,
                ProjectTableColumns.STEP,
                ProjectTableColumns.TAGS,
            ],
        )
        == result
    )
    result = "INSERT INTO scalars_123 (experiment_id, scalar_name, value, step) VALUES ($1, $2, $3, $4)"
    assert (
        SCALARS_DB_UTILS.build_insert_statement(
            "scalars_123",
            [
                ProjectTableColumns.EXPERIMENT_ID,
                ProjectTableColumns.SCALAR_NAME,
                ProjectTableColumns.VALUE,
                ProjectTableColumns.STEP,
            ],
        )
        == result
    )
    result = "INSERT INTO scalars_123 (experiment_id, scalar_name, value, step) VALUES ($1, $2, $3, $4)"
    assert (
        SCALARS_DB_UTILS.build_insert_statement(
            "scalars_123", ["experiment_id", "scalar_name", "value", "step"]
        )
        == result
    )


def test_check_table_existence():
    result = "SHOW CREATE TABLE scalars_123"
    assert SCALARS_DB_UTILS.check_table_existence("scalars_123") == result
    result = "SHOW CREATE TABLE scalars_1234"
    assert SCALARS_DB_UTILS.check_table_existence("scalars_1234") == result
