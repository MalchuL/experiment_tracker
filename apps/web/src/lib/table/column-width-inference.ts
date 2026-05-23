import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";

export type MetricColumnWidthInferenceInput = {
  header: string;
  values: Array<number | null | undefined>;
  minPx: number;
  maxPx: number;
  /** Extra space for padding, sort marks, resize handles, and optional icons. */
  chromePx?: number;
};

function clampPx(value: number, minPx: number, maxPx: number): number {
  return Math.round(Math.max(minPx, Math.min(maxPx, value)));
}

function textWidthEstimatePx(text: string, charPx: number): number {
  return text.length * charPx;
}

/**
 * Deterministic width estimate for metric columns. It intentionally avoids DOM measurement so it
 * works in tests and before the table is painted, while still reflecting the strings users see.
 */
export function inferMetricColumnWidthPx({
  header,
  values,
  minPx,
  maxPx,
  chromePx = 40,
}: MetricColumnWidthInferenceInput): number {
  const headerPx = textWidthEstimatePx(header, 7.5) + chromePx;
  const valuePx =
    Math.max(
      0,
      ...values.map((value) => textWidthEstimatePx(formatMetricScalarForDisplay(value), 8.5))
    ) + chromePx;
  return clampPx(Math.max(headerPx, valuePx), minPx, maxPx);
}
