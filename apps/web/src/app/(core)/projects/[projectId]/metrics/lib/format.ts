import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";

/** Renders a numeric cell; null/empty → em dash. */
export function formatMetricTableCellValue(v: number | null | undefined): string {
  return formatMetricScalarForDisplay(v);
}
