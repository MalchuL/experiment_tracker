/**
 * Tunables for metric number formatting in the web app (tables, DAG, sidebar, editors).
 * Consumed by `@/lib/metrics/metric-value-display`.
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
 * Decimal places used when we render in fixed-point form (`toFixed`).
 */
export const METRIC_DISPLAY_FIXED_DECIMAL_PLACES = 6;

/**
 * If `String(Math.abs(x))` is **longer** than this, we switch to exponential notation.
 * Many IEEE doubles print as a long decimal (e.g. `0.0123123123123123`); this is a cheap
 * “digit budget” before scientific form.
 */
export const METRIC_DISPLAY_MAX_RAW_DECIMAL_STRING_LENGTH =
  METRIC_DISPLAY_FIXED_DECIMAL_PLACES + 6;

/**
 * If the **integer part** of `x.toFixed(METRIC_DISPLAY_FIXED_DECIMAL_PLACES)` has more than
 * this many characters, we switch to exponential so very wide magnitudes do not stretch cells.
 *
 * (Do not use total `toFixed` string length: it always includes fractional digits, so e.g.
 * `100` → `"100.000000"` would falsely exceed a short max-length threshold.)
 */
export const METRIC_DISPLAY_MAX_INTEGER_DIGITS_FOR_FIXED = 15;

/**
 * Fraction digits passed to `toExponential` when we choose scientific notation
 * (read-only UI and logged-metric editor). Keep small so mantissas stay short.
 */
export const METRIC_DISPLAY_EXPONENTIAL_FRACTION_DIGITS = 4;
