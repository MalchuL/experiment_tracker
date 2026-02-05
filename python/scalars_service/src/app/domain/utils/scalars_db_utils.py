from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Sequence, Type


class ProjectTableColumns(Enum):
    TIMESTAMP = "__timestamp__"
    EXPERIMENT_ID = "__experiment_id__"
    STEP = "__step__"
    TAGS = "__tags__"


@dataclass
class ProjectTableColumnsData:
    name: str
    type: Type
    db_type: str


TABLE_COLUMNS_DATA: dict[ProjectTableColumns | str, ProjectTableColumnsData] = {
    ProjectTableColumns.TIMESTAMP: ProjectTableColumnsData(
        name=ProjectTableColumns.TIMESTAMP.value,
        type=datetime,
        db_type="DateTime64(3)",
    ),
    ProjectTableColumns.EXPERIMENT_ID: ProjectTableColumnsData(
        name=ProjectTableColumns.EXPERIMENT_ID.value,
        type=str,
        db_type="String",
    ),
    ProjectTableColumns.STEP: ProjectTableColumnsData(
        name=ProjectTableColumns.STEP.value,
        type=int,
        db_type="Int64",
    ),
    ProjectTableColumns.TAGS: ProjectTableColumnsData(
        name=ProjectTableColumns.TAGS.value,
        type=list,
        db_type="Array(String)",
    ),
}

for column in list(TABLE_COLUMNS_DATA.values()):
    TABLE_COLUMNS_DATA[column.name] = column

BASE_COLUMNS = [
    ProjectTableColumns.TIMESTAMP,
    ProjectTableColumns.EXPERIMENT_ID,
    ProjectTableColumns.STEP,
    ProjectTableColumns.TAGS,
]

BASE_COLUMNS_STR = [column.value for column in BASE_COLUMNS]

SCALAR_COLUMN_TYPE = "Nullable(Float64)"


class ClickHouseScalarsDBUtils:
    def safe_scalars_table_name(self, project_id: str) -> str:
        """
        Validate the table name: only latin letters, numbers, and underscores.
        Ensures that no SQL injection is possible.
        """
        name = f"scalars_{project_id}".lower()
        if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
            raise ValueError("Invalid project_id")
        return name

    def validate_scalar_column_name(self, scalar_name: str) -> str:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$", scalar_name):
            raise ValueError(
                "Invalid scalar_name. Use letters, numbers, and underscores only."
            )
        return scalar_name

    def get_internal_column_names(self) -> set[str]:
        return {column.value for column in ProjectTableColumns}

    def get_base_columns(self) -> list[str]:
        return BASE_COLUMNS_STR

    def build_create_table_statement(
        self, table_name: str, scalar_columns: Sequence[str] | None = None
    ) -> str:
        columns_str = [
            f"{TABLE_COLUMNS_DATA[column].name} {TABLE_COLUMNS_DATA[column].db_type}"
            for column in BASE_COLUMNS
        ]
        if scalar_columns:
            columns_str.extend(
                [f"{col} {SCALAR_COLUMN_TYPE}" for col in scalar_columns]
            )
        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            f"({', '.join(columns_str)}) "
            "ENGINE = MergeTree() "
            f"PARTITION BY toDate({ProjectTableColumns.TIMESTAMP.value}) "
            f"ORDER BY ({ProjectTableColumns.EXPERIMENT_ID.value}, {ProjectTableColumns.STEP.value})"
        )

    def build_alter_table_add_columns_statement(
        self, table_name: str, scalar_columns: Sequence[str]
    ) -> str:
        if not scalar_columns:
            raise ValueError("No scalar columns to add.")
        alters = [
            f"ADD COLUMN IF NOT EXISTS {col} {SCALAR_COLUMN_TYPE}"
            for col in scalar_columns
        ]
        return f"ALTER TABLE {table_name} {', '.join(alters)}"

    def build_drop_table_statement(self, table_name: str) -> str:
        return f"DROP TABLE IF EXISTS {table_name}"

    def build_table_existence_statement(self, table_name: str) -> str:
        return (
            "SELECT count() > 0 "
            "FROM system.tables "
            f"WHERE database = currentDatabase() AND name = '{table_name}'"
        )

    def build_describe_table_statement(self, table_name: str) -> str:
        return f"DESCRIBE TABLE {table_name}"

    def build_select_statement(
        self,
        table_name: str,
        scalar_columns: Sequence[str] | None = None,
        experiment_ids: Sequence[str] | None = None,
    ) -> str:
        columns = BASE_COLUMNS_STR + list(scalar_columns or [])
        select = f"SELECT {', '.join(columns)} FROM {table_name}"
        if experiment_ids:
            ids = ", ".join([f"'{exp_id}'" for exp_id in experiment_ids])
            select += f" WHERE {ProjectTableColumns.EXPERIMENT_ID.value} IN ({ids})"
        select += (
            f" ORDER BY {ProjectTableColumns.EXPERIMENT_ID.value}, "
            f"{ProjectTableColumns.STEP.value}"
        )
        return select

    def get_experiments_ids(self, table_name: str) -> str:
        return f"SELECT DISTINCT {ProjectTableColumns.EXPERIMENT_ID.value} FROM {table_name}"


SCALARS_DB_UTILS = ClickHouseScalarsDBUtils()
