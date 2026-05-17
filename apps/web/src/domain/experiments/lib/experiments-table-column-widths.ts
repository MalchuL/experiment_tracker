import type { ProjectMetric } from "@/domain/projects/types";
import { projectMetricKeyString } from "@/lib/metrics/format-metric-label";

export const EXPERIMENTS_TABLE_GRIP_PX = 56;

const STORAGE_PREFIX = "experiment-tracker:experiments-table:column-widths:";

export const EXPERIMENTS_TABLE_COLUMN = {
  grip: "grip",
  experiment: "experiment",
  status: "status",
  parent: "parent",
  created: "created",
  metricKey: (metric: ProjectMetric) => `metric:${projectMetricKeyString(metric)}`,
} as const;

export type ExperimentsTablePersistedWidths = Record<string, number>;

export function experimentsTableColumnWidthsStorageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

/**
 * Default and minimum width (px) for each non-metric column. Single source for defaults + resize floors.
 */
const EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT = {
  grip: { defaultWidthPx: EXPERIMENTS_TABLE_GRIP_PX, minWidthPx: EXPERIMENTS_TABLE_GRIP_PX },
  /** Wide enough for typical experiment names before the user resizes. */
  experiment: { defaultWidthPx: 320, minWidthPx: 160 },
  status: { defaultWidthPx: 112, minWidthPx: 88 },
  parent: { defaultWidthPx: 160, minWidthPx: 88 },
  created: { defaultWidthPx: 164, minWidthPx: 120 },
} as const;

/** Metric columns — same as metrics pivot (`size: 120`, `minSize: 72` in `use-metric-table-columns.tsx`). */
const EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT = {
  defaultWidthPx: 160,
  minWidthPx: 72,
} as const;

export const EXPERIMENTS_TABLE_DEFAULT_METRIC_COLUMN_PX =
  EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT.defaultWidthPx;

export const EXPERIMENTS_TABLE_DEFAULT_WIDTHS: Record<string, number> = {
  grip: EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT.grip.defaultWidthPx,
  experiment: EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT.experiment.defaultWidthPx,
  status: EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT.status.defaultWidthPx,
  parent: EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT.parent.defaultWidthPx,
  created: EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT.created.defaultWidthPx,
};

export function metricColumnId(metric: ProjectMetric): string {
  return EXPERIMENTS_TABLE_COLUMN.metricKey(metric);
}

export function experimentsTableColumnMinWidth(columnId: string): number {
  if (columnId in EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT) {
    return EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT[
      columnId as keyof typeof EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT
    ].minWidthPx;
  }
  if (columnId.startsWith("metric:")) return EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT.minWidthPx;
  return 60;
}

export function experimentsTableColumnWidthFallback(columnId: string): number {
  if (columnId === "grip") return EXPERIMENTS_TABLE_GRIP_PX;
  if (columnId.startsWith("metric:")) return EXPERIMENTS_TABLE_DEFAULT_METRIC_COLUMN_PX;
  const w = EXPERIMENTS_TABLE_DEFAULT_WIDTHS[columnId as keyof typeof EXPERIMENTS_TABLE_DEFAULT_WIDTHS];
  return typeof w === "number" ? w : 120;
}

export function buildDefaultExperimentsTableWidths(metrics: ProjectMetric[]): Record<string, number> {
  const out: Record<string, number> = { ...EXPERIMENTS_TABLE_DEFAULT_WIDTHS };
  for (const m of metrics) {
    out[metricColumnId(m)] = EXPERIMENTS_TABLE_DEFAULT_METRIC_COLUMN_PX;
  }
  return out;
}

export function clampExperimentsColumnWidth(columnId: string, width: number): number {
  if (columnId === "grip") return EXPERIMENTS_TABLE_GRIP_PX;
  return Math.round(Math.max(experimentsTableColumnMinWidth(columnId), width));
}

export function mergeExperimentsTableWidths(
  defaults: Record<string, number>,
  persisted: ExperimentsTablePersistedWidths | null
): Record<string, number> {
  const next = { ...defaults };
  if (!persisted) return next;
  for (const [k, v] of Object.entries(persisted)) {
    if (k === "grip" || typeof v !== "number" || !Number.isFinite(v)) continue;
    if (next[k] === undefined) continue;
    next[k] = clampExperimentsColumnWidth(k, v);
  }
  next.grip = EXPERIMENTS_TABLE_GRIP_PX;
  return next;
}

export function loadExperimentsTableWidths(projectId: string): ExperimentsTablePersistedWidths | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(experimentsTableColumnWidthsStorageKey(projectId));
    if (!raw) return null;
    return JSON.parse(raw) as ExperimentsTablePersistedWidths;
  } catch {
    return null;
  }
}

export function saveExperimentsTableWidths(
  projectId: string,
  widths: Record<string, number>
): void {
  if (typeof window === "undefined") return;
  try {
    const { grip: _g, ...rest } = widths;
    localStorage.setItem(experimentsTableColumnWidthsStorageKey(projectId), JSON.stringify(rest));
  } catch {
    /* ignore */
  }
}
