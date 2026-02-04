from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import lru_cache
import re
from typing import Any, Sequence, Type


class ProjectTableColumns(Enum):
    TIMESTAMP = "timestamp"
    EXPERIMENT_ID = "experiment_id"
    SCALAR_NAME = "scalar_name"
    VALUE = "value"
    STEP = "step"
    TAGS = "tags"


@dataclass
class ProjectTableColumnsData:
    name: str
    type: Type[Any]
    db_type: str


TABLE_COLUMNS_DATA: dict[ProjectTableColumns | str, ProjectTableColumnsData] = {
    ProjectTableColumns.TIMESTAMP: ProjectTableColumnsData(
        name=ProjectTableColumns.TIMESTAMP.value,
        type=datetime,
        db_type="TIMESTAMP NOT NULL",
    ),
    ProjectTableColumns.EXPERIMENT_ID: ProjectTableColumnsData(
        name=ProjectTableColumns.EXPERIMENT_ID.value, type=str, db_type="SYMBOL"
    ),
    ProjectTableColumns.SCALAR_NAME: ProjectTableColumnsData(
        name=ProjectTableColumns.SCALAR_NAME.value, type=str, db_type="SYMBOL"
    ),
    ProjectTableColumns.VALUE: ProjectTableColumnsData(
        name=ProjectTableColumns.VALUE.value, type=float, db_type="DOUBLE NOT NULL"
    ),
    ProjectTableColumns.STEP: ProjectTableColumnsData(
        name=ProjectTableColumns.STEP.value, type=int, db_type="INT"
    ),
    ProjectTableColumns.TAGS: ProjectTableColumnsData(
        name=ProjectTableColumns.TAGS.value, type=list[str], db_type="STRING"
    ),
}

# Make the dictionary keys the column names
for column in list(TABLE_COLUMNS_DATA.values()):
    TABLE_COLUMNS_DATA[column.name] = column


COLUMNS_ORDER = [
    ProjectTableColumns.TIMESTAMP,
    ProjectTableColumns.EXPERIMENT_ID,
    ProjectTableColumns.SCALAR_NAME,
    ProjectTableColumns.VALUE,
    ProjectTableColumns.STEP,
    ProjectTableColumns.TAGS,
]

COLUMNS_ORDER_STR = [column.value for column in COLUMNS_ORDER]

TIMESTAMP_COLUMN_NAME = TABLE_COLUMNS_DATA[ProjectTableColumns.TIMESTAMP].name


class QuestDBScalarsDBUtils:
    def safe_scalars_table_name(self, project_id: str) -> str:
        """
        Validate the table name: only latin letters, numbers, and underscores.
        Ensures that no SQL injection is possible.

        Args:
            project_id (str): The project ID to validate. Must be less than 64 characters and start with a letter or underscore.

        Returns:
            str: The validated table name.
        Example:
            scalars_123
        """
        name = f"scalars_{project_id}".lower()
        if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
            raise ValueError("Invalid project_id")
        return name

    def get_table_columns(self) -> list[str]:
        return COLUMNS_ORDER_STR

    @staticmethod
    @lru_cache(maxsize=1000)
    def _build_insert_statement_data(
        columns: Sequence[str | ProjectTableColumns],
    ) -> str:
        """Build the insert statement data for the given columns.

        Args:
            columns (Sequence[str | ProjectTableColumns]): The columns to insert.

        Returns:
            str: The insert statement data.
        Example:
            (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)
        """
        columns_str = [TABLE_COLUMNS_DATA[column].name for column in columns]
        return f"({', '.join(columns_str)}) VALUES ({', '.join([f'${i+1}' for i in range(len(columns_str))])})"

    def build_insert_statement(
        self, table_name: str, columns: list[str | ProjectTableColumns] | None = None
    ) -> str:
        """Build the insert statement for the given table name.

        Args:
            table_name (str): The name of the table to insert into.

        Returns:
            str: The insert statement.
        Example:
            INSERT INTO scalars_123 (timestamp, experiment_id, scalar_name, value, step, tags) VALUES ($1, $2, $3, $4, $5, $6)
        """
        if columns is None:
            select_columns = COLUMNS_ORDER_STR
        else:
            select_columns = [TABLE_COLUMNS_DATA[column].name for column in columns]
        return f"INSERT INTO {table_name} {self._build_insert_statement_data(tuple(select_columns))}"

    def build_select_statement(
        self, table_name: str, columns: list[str | ProjectTableColumns] | None = None
    ) -> str:
        """Build the select statement for the given table name and columns.

        Args:
            table_name (str): The name of the table to select from.
            columns (list[str | ProjectTableColumns] | None): The columns to select. If None, select all columns.

        Returns:
            str: The select statement.
        Example:
            SELECT timestamp, experiment_id, scalar_name, value, step, tags FROM scalars_123
        """
        select_columns: list[str]
        if columns is None:
            select_columns = COLUMNS_ORDER_STR
        else:
            select_columns = [TABLE_COLUMNS_DATA[column].name for column in columns]

        return f"SELECT {', '.join(select_columns)} FROM {table_name}"

    def build_select_statement_with_experiment_id(
        self, table_name: str, experiment_id: str
    ) -> str:
        return (
            self.build_select_statement(table_name)
            + f" WHERE experiment_id = '{experiment_id}'"
        )

    def build_create_table_statement(self, table_name: str) -> str:
        """Build the create table statement for the given table name.

        Args:
            table_name (str): The name of the table to create.

        Returns:
            str: The create table statement.
        Example:
            CREATE TABLE scalars_123 (
                timestamp TIMESTAMP NOT NULL,
                experiment_id SYMBOL,
                scalar_name SYMBOL,
                value DOUBLE NOT NULL,
                step INT,
                tags STRING
            ) TIMESTAMP(timestamp) PARTITION BY DAY
        """
        columns_str = [
            f"{TABLE_COLUMNS_DATA[column].name} {TABLE_COLUMNS_DATA[column].db_type}"
            for column in COLUMNS_ORDER
        ]
        return f"CREATE TABLE {table_name} ({', '.join(columns_str)}) TIMESTAMP({TIMESTAMP_COLUMN_NAME}) PARTITION BY DAY"

    def build_drop_table_statement(self, table_name: str) -> str:
        """Build the drop table statement for the given table name.

        Args:
            table_name (str): The name of the table to drop.

        Returns:
            str: The drop table statement.
        Example:
            DROP TABLE scalars_123
        """
        return f"DROP TABLE {table_name}"

    def check_table_existence(self, table_name: str) -> str:
        """Check if the table exists in the database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        return f"SHOW CREATE TABLE {table_name}"

    def get_experiments_ids(self, table_name: str) -> str:
        """Get the experiments IDs from the table.

        Args:
            table_name (str): The name of the table to get the experiments IDs from.

        Returns:
            list[str]: The experiments IDs.
        """
        return f"SELECT DISTINCT experiment_id FROM {table_name}"


SCALARS_DB_UTILS = QuestDBScalarsDBUtils()
