/**
 * Tunables for metric number formatting in the web app (tables, DAG, sidebar, editors).
 * Scalar formatting uses mathjs `format` with `notation: 'auto'` — see
 * `@/lib/metrics/mathjs-metric-format` (`formatValue`, `METRIC_FORMAT_OPTIONS`).
 */

/**
 * Values closer than this (absolute difference) are treated as **equal** for:
 * - parent delta display → formatted as `"0"`, no up/down arrow;
 * - `metricIsBetterThanParent` in `metric-value-display.ts` → `null` (no green/red).
 *
 * Reduces float noise showing fake tiny changes.
 */
export const METRIC_DISPLAY_TIE_EPSILON = 1e-10;

/**
 * Significant digits passed to mathjs `format(..., { notation: 'auto', precision })` for metrics.
 */
export const METRIC_DISPLAY_AUTO_FORMAT_PRECISION = 7;

/**
 * Symmetric exponent band for `notation: 'auto'`: plain decimals when the scaled exponent is in
 * `[-bound, bound)` (see mathjs `lowerExp` / `upperExp`).
 */
export const METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND = 6;
