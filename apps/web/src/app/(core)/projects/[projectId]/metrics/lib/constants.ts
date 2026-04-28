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
