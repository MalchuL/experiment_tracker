from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Sequence, Type
from uuid import UUID

from config import get_settings


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
        type=UUID,
        db_type="UUID",
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
    def _escape_sql_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _format_datetime_literal(self, value: datetime) -> str:
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _format_uuid_literal(self, value: UUID) -> str:
        if not isinstance(value, UUID):
            raise ValueError("Value is not a UUID")
        return str(value)

    def get_mapping_table_name(self) -> str:
        """Get the mapping table name that stores the mapping of scalar names to internal column names.

        Returns:
            str: The mapping table name.
        """
        return get_settings().SCALARS_MAPPING_TABLE

    def safe_scalars_table_name(self, project_id: UUID) -> str:
        """
        Validate the table name: only latin letters, numbers, and underscores.
        Ensures that no SQL injection is possible.
        Keep in mind that table name is HEX string.
        """
        normalized_project_id = project_id.hex
        name = f"scalars_{normalized_project_id}".lower()
        if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
            raise ValueError("Invalid project_id")
        return name

    def safe_last_logged_table_name(self, project_id: UUID) -> str:
        """
        Validate per-project last logged table name.
        Keep in mind that table name is HEX string.
        """
        normalized_project_id = project_id.hex
        name = f"scalars_last_logged_{normalized_project_id}".lower()
        if not re.match(r"^[a-z_][a-z0-9_]{1,63}$", name):
            raise ValueError("Invalid project_id")
        return name

    def validate_scalar_column_name(self, scalar_name: str) -> str | None:
        """Validate the scalar column name: only latin letters, numbers, and underscores.

        Args:
            scalar_name (str): The scalar name.

        Returns:
            str | None: The validated scalar column name.
        """
        normalized = re.sub(r"\s+", "_", scalar_name.strip())
        if not normalized:
            return "_empty_"
        normalized = normalized[:64]
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$", normalized):
            return None
        return normalized

    def get_base_columns(self) -> list[str]:
        """Get the base columns that are always present in the scalars table.

        Returns:
            list[str]: The base columns.
        """
        return BASE_COLUMNS_STR

    def build_create_scalars_table_statement(
        self, table_name: str, scalar_columns: Sequence[str] | None = None
    ) -> str:
        """Build the CREATE TABLE statement for the scalars table.

        Args:
            table_name (str): The table name.
            scalar_columns (Sequence[str] | None): The scalar columns.

        Returns:
            str: The CREATE TABLE statement.
        """
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

    def build_create_mapping_table_statement(self) -> str:
        """Build the CREATE TABLE statement for the mapping table.

        Returns:
            str: The CREATE TABLE statement.
        """
        return (
            f"CREATE TABLE IF NOT EXISTS {self.get_mapping_table_name()} "
            "(project_id UUID, mapping Map(String, String), updated_at DateTime64(3)) "
            "ENGINE = ReplacingMergeTree(updated_at) "
            "ORDER BY project_id"
        )

    def build_create_last_logged_table_statement(self, table_name: str) -> str:
        """Build the CREATE TABLE statement for the last logged table.

        Args:
            table_name (str): The table name.

        Returns:
            str: The CREATE TABLE statement.
        """
        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            "(experiment_id UUID, last_modified DateTime64(3)) "
            "ENGINE = ReplacingMergeTree(last_modified) "
            "ORDER BY experiment_id"
        )

    def build_upsert_last_logged_statement(
        self,
        table_name: str,
        experiment_id: UUID,
        last_modified: datetime,
    ) -> str:
        """Build the UPSERT statement for the last logged table.

        Args:
            table_name (str): The table name.
            experiment_id (UUID): The experiment ID.
            last_modified (datetime): The last modified timestamp.

        Returns:
            str: The UPSERT statement.
        """
        last_modified_value = self._format_datetime_literal(last_modified)
        experiment_uuid = self._format_uuid_literal(experiment_id)
        return (
            f"INSERT INTO {table_name} (experiment_id, last_modified) VALUES "
            f"('{experiment_uuid}', toDateTime64('{last_modified_value}', 3))"
        )

    def build_select_last_logged_statement(
        self,
        table_name: str,
        experiment_ids: Sequence[UUID] | None = None,
    ) -> str:
        """Build the SELECT statement for the last logged table.

        Args:
            table_name (str): The table name.
            experiment_ids (Sequence[UUID] | None): The experiment IDs.

        Returns:
            str: The SELECT statement.
        """
        where_clause = ""
        if experiment_ids:
            uuid_ids = ", ".join(
                [f"'{self._format_uuid_literal(exp_id)}'" for exp_id in experiment_ids]
            )
            where_clause = f" WHERE experiment_id IN ({uuid_ids})"
        return (
            "SELECT experiment_id, max(last_modified) AS last_modified "
            f"FROM {table_name}{where_clause} "
            "GROUP BY experiment_id"
        )

    def build_alter_table_add_columns_statement(
        self, table_name: str, scalar_columns: Sequence[str]
    ) -> str:
        """Build the ALTER TABLE statement to add columns to the scalars table.

        Args:
            table_name (str): The table name.
            scalar_columns (Sequence[str]): The scalar columns to add.

        Returns:
            str: The ALTER TABLE statement.
        """
        if not scalar_columns:
            raise ValueError("No scalar columns to add.")
        alters = [
            f"ADD COLUMN IF NOT EXISTS {col} {SCALAR_COLUMN_TYPE}"
            for col in scalar_columns
        ]
        return f"ALTER TABLE {table_name} {', '.join(alters)}"

    def build_drop_table_statement(self, table_name: str) -> str:
        """Build the DROP TABLE statement.

        Args:
            table_name (str): The table name.

        Returns:
            str: The DROP TABLE statement.
        """
        return f"DROP TABLE IF EXISTS {table_name}"

    def build_table_existence_statement(self, table_name: str) -> str:
        """Build statement to check if the table exists. Returns count of rows > 0 if table exists.

        Args:
            table_name (str): The table name.

        Returns:
            str: The SQL statement to check if the table exists.
        """
        return (
            "SELECT count() > 0 "
            "FROM system.tables "
            f"WHERE database = currentDatabase() AND name = '{table_name}'"
        )

    def build_describe_table_statement(self, table_name: str) -> str:
        """Build the DESCRIBE TABLE statement.

        Args:
            table_name (str): The table name.

        Returns:
            str: The DESCRIBE TABLE statement.
        """
        return f"DESCRIBE TABLE {table_name}"

    def build_select_statement(
        self,
        table_name: str,
        scalar_columns: Sequence[str] | None = None,
        experiment_ids: Sequence[UUID] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> str:
        """Build the SELECT statement for the scalars table.

        Args:
            table_name (str): The table name.
            scalar_columns (Sequence[str] | None): The scalar columns.
            experiment_ids (Sequence[UUID] | None): The experiment IDs.
            start_time (datetime | None): The start time.
            end_time (datetime | None): The end time.

        Returns:
            str: The SELECT statement.
        """
        columns = BASE_COLUMNS_STR + list(scalar_columns or [])
        select = f"SELECT {', '.join(columns)} FROM {table_name}"
        where_clauses: list[str] = []
        if experiment_ids:
            uuids = ", ".join(
                [f"'{self._format_uuid_literal(exp_id)}'" for exp_id in experiment_ids]
            )
            where_clauses.append(
                f"{ProjectTableColumns.EXPERIMENT_ID.value} IN ({uuids})"
            )
        if start_time is not None:
            where_clauses.append(
                f"{ProjectTableColumns.TIMESTAMP.value} >= "
                f"toDateTime64('{self._format_datetime_literal(start_time)}', 3)"
            )
        if end_time is not None:
            where_clauses.append(
                f"{ProjectTableColumns.TIMESTAMP.value} <= "
                f"toDateTime64('{self._format_datetime_literal(end_time)}', 3)"
            )
        if where_clauses:
            select += f" WHERE {' AND '.join(where_clauses)}"
        # TODO maybe remove ORDER BY and let the client sort the results?
        select += (
            f" ORDER BY {ProjectTableColumns.EXPERIMENT_ID.value}, "
            f"{ProjectTableColumns.STEP.value}"
        )
        return select

    def build_select_mapping_statement(self, project_id: UUID) -> str:
        """Select mapping for scalar name to internal column name for a given project ID.

        Args:
            project_id (UUID): The project ID.

        Returns:
            str: The SQL statement to select the mapping.
        """
        project_uuid = self._format_uuid_literal(project_id)
        return (
            f"SELECT mapping FROM {self.get_mapping_table_name()} "
            f"WHERE project_id = '{project_uuid}' "
            "ORDER BY updated_at DESC LIMIT 1"
        )

    def build_delete_mapping_statement(self, project_id: UUID) -> str:
        """Delete mapping for a given project ID.

        Args:
            project_id (UUID): The project ID.

        Returns:
            str: The SQL statement to delete the mapping.
        """
        project_uuid = self._format_uuid_literal(project_id)
        return (
            f"ALTER TABLE {self.get_mapping_table_name()} "
            f"DELETE WHERE project_id = '{project_uuid}'"
        )

    def build_experiments_ids_statement(self, table_name: str) -> str:
        """Build statement to get all experiment IDs for a given table name.

        Args:
            table_name (str): The table name.

        Returns:
            str: The SQL statement to select the experiment IDs.
        """
        return f"SELECT DISTINCT {ProjectTableColumns.EXPERIMENT_ID.value} FROM {table_name}"


SCALARS_DB_UTILS = ClickHouseScalarsDBUtils()
