import { format } from "mathjs/number";
import {
  METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND,
  METRIC_DISPLAY_AUTO_FORMAT_PRECISION,
} from "@/lib/constants/metric-display";

/** mathjs `format` options used for metric scalars, deltas, and editor drafts (read `format` docs for `notation: 'auto'`). */
export const METRIC_FORMAT_OPTIONS = {
  notation: "auto" as const,
  precision: METRIC_DISPLAY_AUTO_FORMAT_PRECISION,
  lowerExp: -METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND,
  upperExp: METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND,
};

export type MetricMathjsFormatOverrides = {
  precision?: number;
  expBound?: number;
};

function resolvedOptions(overrides?: MetricMathjsFormatOverrides) {
  const precision = overrides?.precision ?? METRIC_DISPLAY_AUTO_FORMAT_PRECISION;
  const expBound = overrides?.expBound ?? METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND;
  return {
    notation: "auto" as const,
    precision,
    lowerExp: -expBound,
    upperExp: expBound,
  };
}

/** Default metric number → string via mathjs (same as in `mathjs-format.test.ts`). */
export function formatValue(value: number, overrides?: MetricMathjsFormatOverrides): string {
  return format(value, resolvedOptions(overrides));
}

/**
 * Plain decimal string for metric editors (focus / “full” value). Uses mathjs `notation: 'fixed'`
 * so magnitudes that {@link formatValue} would show as `1e-7` appear as `0.0000001`.
 */
export function formatValueNonExponential(value: number): string {
  return format(value, { notation: "fixed" });
}
