import type { MetricsTableRow } from "./types";

const FIXED_COLUMN_IDS = new Set(["experiment", "experimentId", "createdAt"]);

/** Middle segment of column order (metric names only). */
export function metricNamesFromColumnOrder(columnOrder: string[]): string[] {
  return columnOrder.filter((c) => !FIXED_COLUMN_IDS.has(c));
}

/** Rebuild full pivot column order from an ordered metric name list. */
export function rebuildColumnOrder(metricNames: string[]): string[] {
  return ["experiment", ...metricNames, "experimentId", "createdAt"];
}

/** Merge API row order with a session visual order: keep known IDs, append new ones, drop stale. */
export function syncExperimentRowOrder(
  currentOrder: string[],
  rows: MetricsTableRow[]
): string[] {
  const rowIds = rows.map((r) => r.experimentId);
  const rowIdSet = new Set(rowIds);
  const next: string[] = [];
  for (const id of currentOrder) {
    if (rowIdSet.has(id) && !next.includes(id)) next.push(id);
  }
  for (const id of rowIds) {
    if (!next.includes(id)) next.push(id);
  }
  return next;
}

/** Apply visual row order; unknown IDs fall back to createdAt desc then experimentId. */
export function orderRowsByIds(
  rows: MetricsTableRow[],
  orderIds: string[]
): MetricsTableRow[] {
  if (orderIds.length === 0) return rows;
  const indexById = new Map(orderIds.map((id, i) => [id, i]));
  return [...rows].sort((a, b) => {
    const ia = indexById.get(a.experimentId);
    const ib = indexById.get(b.experimentId);
    if (ia != null && ib != null) return ia - ib;
    if (ia != null) return -1;
    if (ib != null) return 1;
    const ta = a.createdAt !== "" ? Date.parse(a.createdAt) : 0;
    const tb = b.createdAt !== "" ? Date.parse(b.createdAt) : 0;
    if (Number.isFinite(tb) && Number.isFinite(ta) && tb !== ta) return tb - ta;
    return b.experimentId.localeCompare(a.experimentId);
  });
}

/** Reorder a visible subset within a full order list (e.g. table rows while some are hidden). */
export function reorderIdSubset(
  fullOrder: string[],
  subsetIds: string[],
  activeId: string,
  overId: string
): string[] {
  const oldIndex = subsetIds.indexOf(activeId);
  const newIndex = subsetIds.indexOf(overId);
  if (oldIndex < 0 || newIndex < 0) return fullOrder;
  const newSubset = [...subsetIds];
  const [moved] = newSubset.splice(oldIndex, 1);
  newSubset.splice(newIndex, 0, moved!);
  const subsetSet = new Set(subsetIds);
  const result = [...fullOrder];
  let si = 0;
  for (let i = 0; i < result.length; i++) {
    if (subsetSet.has(result[i]!)) {
      result[i] = newSubset[si]!;
      si++;
    }
  }
  return result;
}
