"""ClickHouse SELECT strings for usage, compaction, and storage table listing.

Identifiers (``table_name``, storage column names) must be validated by
``ClickHouseScalarsDBUtils`` (``safe_*_table_name``, ``validate_scalar_storage_column_name``)
before calling these helpers. UUID literals for ``experiment_id`` are formatted by the
caller.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScalarsSelectSql:
    """Composable SELECT snippets; keep raw SQL out of domain services."""

    def count_all_rows(self, table_name: str) -> str:
        return f"SELECT count() FROM {table_name}"

    def count_non_null_column(self, table_name: str, column_name: str) -> str:
        return f"SELECT count() FROM {table_name} WHERE {column_name} IS NOT NULL"

    def sum_bytes_on_disk_active_parts(self, table_literal: str) -> str:
        """``table_literal`` must be safe for single-quoted ``system.parts.table`` (escaped)."""
        return (
            "SELECT coalesce(sum(bytes_on_disk), 0) FROM system.parts "
            f"WHERE database = currentDatabase() AND table = '{table_literal}' AND active"
        )

    def count_rows_for_experiment(
        self, table_name: str, experiment_id_column: str, experiment_uuid_literal: str
    ) -> str:
        return (
            f"SELECT count() FROM {table_name} "
            f"WHERE {experiment_id_column} = '{experiment_uuid_literal}'"
        )

    @staticmethod
    def managed_tables_predicate_sql() -> str:
        return (
            "database = currentDatabase() "
            "AND (name LIKE 'scalars_%' OR name LIKE 'artifacts_info_%')"
        )

    def list_tables_count(self, extra_predicate: str = "") -> str:
        base = self.managed_tables_predicate_sql()
        return f"SELECT count() FROM system.tables WHERE {base}{extra_predicate}"

    def list_tables_page(
        self, extra_predicate: str = "", limit: int = 50, offset: int = 0
    ) -> str:
        lim = max(1, min(int(limit), 200))
        off = max(0, int(offset))
        base = self.managed_tables_predicate_sql()
        return (
            "SELECT name, total_rows, total_bytes FROM system.tables "
            f"WHERE {base}{extra_predicate} ORDER BY name LIMIT {lim} OFFSET {off}"
        )


SCALARS_SELECT_SQL = ScalarsSelectSql()
