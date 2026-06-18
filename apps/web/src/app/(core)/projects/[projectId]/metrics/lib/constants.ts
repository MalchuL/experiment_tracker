import type { MetricsTableRow } from "./types";

/** localStorage key for label / column size / order (excludes edit-session state). */
export const persistedMetricsUiKey = (projectId: string) => `et-project-metrics-ui:${projectId}`;

/** Map cell click cycle step → background class. Session state until full reload. */
export const METRIC_CELL_TINTS: Record<1 | 2 | 3 | 4, string> = {
  1: "bg-red-200/80 dark:bg-red-900/50",
  2: "bg-emerald-200/80 dark:bg-emerald-900/50",
  3: "bg-sky-200/80 dark:bg-sky-900/50",
  4: "bg-orange-200/80 dark:bg-orange-900/50",
};

/** Key for per-cell color marks in the edit-session `cellTints` map. */
export const metricCellStyleKey = (row: Pick<MetricsTableRow, "experimentId">, metricName: string) =>
  `${row.experimentId}::${metricName}`;

/** Edit-mode-only column: row visibility in the exported report. */
export const SHOW_IN_REPORT_COLUMN_ID = "showInReport";
/** Checkbox (16px) + minimal horizontal padding. */
export const SHOW_IN_REPORT_COLUMN_PX = 36;

/** Per-cell bottom rule (`border-separate` tables need borders on cells, not rows). */
export const METRICS_TABLE_ROW_BORDER_CLASS = "box-border border-b border-border";
