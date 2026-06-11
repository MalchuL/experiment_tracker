import type { ProjectMetric } from "@/domain/projects/types";
import { projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import type { ColumnWidthPolicy } from "@/lib/table/column-width-policy";

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

/** Metric columns: inferred width between min/max unless the user persisted a px override. */
const EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT = {
  policy: { mode: "auto", minPx: 72, maxPx: 260 } as const satisfies ColumnWidthPolicy,
} as const;

/** Used before content-based metric widths have been inferred. */
export const EXPERIMENTS_TABLE_METRIC_AUTO_MIN_PX = EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT.policy.minPx;

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

export function experimentsTableColumnPolicy(columnId: string): ColumnWidthPolicy {
  if (columnId in EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT) {
    const c = EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT[
      columnId as keyof typeof EXPERIMENTS_TABLE_STATIC_COLUMN_LAYOUT
    ];
    return {
      mode: "fixed",
      defaultPx: c.defaultWidthPx,
      minPx: c.minWidthPx,
      maxPx: Math.max(c.minWidthPx, c.defaultWidthPx * 2),
    };
  }
  if (columnId.startsWith("metric:")) {
    return { ...EXPERIMENTS_TABLE_METRIC_COLUMN_LAYOUT.policy };
  }
  return { mode: "fixed", defaultPx: 120, minPx: 60, maxPx: 480 };
}

export function experimentsTableColumnMinWidth(columnId: string): number {
  return experimentsTableColumnPolicy(columnId).minPx;
}

export function experimentsTableColumnWidthFallback(columnId: string): number {
  if (columnId === "grip") return EXPERIMENTS_TABLE_GRIP_PX;
  if (columnId.startsWith("metric:")) return EXPERIMENTS_TABLE_METRIC_AUTO_MIN_PX;
  const p = experimentsTableColumnPolicy(columnId);
  return p.mode === "fixed" ? p.defaultPx : p.minPx;
}

export function buildDefaultExperimentsTableWidths(
  metrics: ProjectMetric[],
  inferredMetricWidths: Record<string, number> = {}
): Record<string, number> {
  const out: Record<string, number> = { ...EXPERIMENTS_TABLE_DEFAULT_WIDTHS };
  for (const m of metrics) {
    const id = metricColumnId(m);
    out[id] = clampExperimentsColumnWidth(
      id,
      inferredMetricWidths[id] ?? EXPERIMENTS_TABLE_METRIC_AUTO_MIN_PX
    );
  }
  return out;
}

export function clampExperimentsColumnWidth(columnId: string, width: number): number {
  if (columnId === "grip") return EXPERIMENTS_TABLE_GRIP_PX;
  if (!Number.isFinite(width)) return experimentsTableColumnWidthFallback(columnId);
  return Math.max(1, Math.round(width));
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
    const rest = { ...widths };
    delete rest.grip;
    localStorage.setItem(experimentsTableColumnWidthsStorageKey(projectId), JSON.stringify(rest));
  } catch {
    /* ignore */
  }
}

const PIN_LEAD_STORAGE_PREFIX = "experiment-tracker:experiments-table:pin-lead:";

export function experimentsTablePinLeadStorageKey(projectId: string): string {
  return `${PIN_LEAD_STORAGE_PREFIX}${projectId}`;
}

export function loadExperimentsTablePinLead(projectId: string): boolean {
  if (typeof window === "undefined") return true;
  try {
    const raw = localStorage.getItem(experimentsTablePinLeadStorageKey(projectId));
    if (raw === null) return true;
    return raw === "1" || raw === "true";
  } catch {
    return true;
  }
}

export function saveExperimentsTablePinLead(projectId: string, pin: boolean): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(experimentsTablePinLeadStorageKey(projectId), pin ? "1" : "0");
  } catch {
    /* ignore */
  }
}

const WRAP_NAMES_STORAGE_PREFIX = "experiment-tracker:experiments-table:wrap-names:";

export function experimentsTableWrapNamesStorageKey(projectId: string): string {
  return `${WRAP_NAMES_STORAGE_PREFIX}${projectId}`;
}

export function loadExperimentsTableWrapNames(projectId: string): boolean {
  if (typeof window === "undefined") return true;
  try {
    const raw = localStorage.getItem(experimentsTableWrapNamesStorageKey(projectId));
    if (raw === null) return true;
    return raw === "1" || raw === "true";
  } catch {
    return true;
  }
}

export function saveExperimentsTableWrapNames(projectId: string, wrap: boolean): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(experimentsTableWrapNamesStorageKey(projectId), wrap ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function computeExperimentsTableTotalWidthPx(
  resolved: Record<string, number>,
  _metricPxOverrideKeys: Set<string>,
  projectMetrics: ProjectMetric[]
): number {
  let sum = 0;
  const staticIds = [
    EXPERIMENTS_TABLE_COLUMN.grip,
    EXPERIMENTS_TABLE_COLUMN.experiment,
    EXPERIMENTS_TABLE_COLUMN.status,
    EXPERIMENTS_TABLE_COLUMN.parent,
    EXPERIMENTS_TABLE_COLUMN.created,
  ] as const;
  for (const id of staticIds) {
    sum += resolved[id] ?? experimentsTableColumnWidthFallback(id);
  }
  for (const m of projectMetrics) {
    const id = metricColumnId(m);
    const r = resolved[id] ?? experimentsTableColumnWidthFallback(id);
    sum += r;
  }
  return sum;
}
