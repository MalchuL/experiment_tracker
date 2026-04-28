/** Renders a numeric cell; null/empty → em dash. */
export function formatMetricTableCellValue(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return Number.isFinite(v) ? v.toFixed(4) : "—";
}
