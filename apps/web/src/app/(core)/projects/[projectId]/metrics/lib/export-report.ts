import type { Table } from "@tanstack/react-table";
import type { MetricsTableRow } from "./types";

/** File headers: `experiment` column → readable name; API field names for meta columns. */
const COLUMN_ID_TO_EXPORT: Record<string, string> = {
  experiment: "experiment_name",
  experimentId: "experimentId",
  createdAt: "createdAt",
};

function exportKey(columnId: string) {
  return COLUMN_ID_TO_EXPORT[columnId] ?? columnId;
}

function csvCell(s: string): string {
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function stringifyValue(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "number" && !Number.isFinite(v)) return "";
  return String(v);
}

function jsonValue(v: unknown): string | number | null {
  if (v == null) return null;
  if (typeof v === "number" && !Number.isFinite(v)) return null;
  return v as string | number | null;
}

/** Markdown pipe table: escape cells so `|` in values does not break columns. */
function markdownEscapeCell(s: string): string {
  return s.replace(/\r?\n/g, " ").replace(/\|/g, "\\|");
}

/**
 * Exports the **currently visible** columns in **row order** as shown in the table
 * (after sorting). Suitable for the report view.
 */
export function downloadTableReport(
  table: Table<MetricsTableRow>,
  format: "csv" | "json" | "markdown",
  fileBase: string
) {
  const cols = table.getVisibleLeafColumns();
  if (cols.length === 0) return;

  const rowModels = table.getRowModel().rows;
  const names = cols.map((c) => exportKey(c.id));

  if (format === "csv") {
    const head = names.map((n) => csvCell(n)).join(",");
    const body = rowModels.map((row) =>
      cols
        .map((col) => {
          const raw = row.getValue(col.id);
          return csvCell(stringifyValue(raw));
        })
        .join(",")
    );
    const text = "\uFEFF" + [head, ...body].join("\n");
    triggerDownload(`${sanitizeFileName(fileBase)}.csv`, text, "text/csv;charset=utf-8");
    return;
  }

  if (format === "json") {
    /** Common tabular shape: first row = headers, then one array per data row. */
    const asLists: (string | number | null)[][] = [
      names,
      ...rowModels.map((row) =>
        cols.map((col) => jsonValue(row.getValue(col.id)) as string | number | null)
      ),
    ];
    const text = JSON.stringify(asLists, null, 2);
    triggerDownload(
      `${sanitizeFileName(fileBase)}.json`,
      text,
      "application/json;charset=utf-8"
    );
    return;
  }

  const headerLine = "| " + names.map((n) => markdownEscapeCell(n)).join(" | ") + " |";
  const sepLine = "| " + names.map(() => "---").join(" | ") + " |";
  const bodyLines = rowModels.map((row) => {
    const cells = cols.map((col) => markdownEscapeCell(stringifyValue(row.getValue(col.id))));
    return "| " + cells.join(" | ") + " |";
  });
  const text = [headerLine, sepLine, ...bodyLines].join("\n");
  triggerDownload(
    `${sanitizeFileName(fileBase)}.md`,
    text,
    "text/markdown;charset=utf-8"
  );
}

function sanitizeFileName(s: string) {
  return s.replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-|-$/g, "") || "report";
}

function triggerDownload(filename: string, data: string, type: string) {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
