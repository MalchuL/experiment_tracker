/**
 * Defaults for **displaying** metric numbers in the UI (tables, DAG, sidebar, selected metrics,
 * logged-metric value when the field is **not** focused).
 *
 * - **Digits and scientific form:** `METRIC_DISPLAY_AUTO_FORMAT_PRECISION`,
 *   `METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND`
 * - **Comparing two values** (parent vs child, deltas): `METRIC_DISPLAY_TIE_EPSILON` — does not
 *   change how a single number is written, only whether a tiny gap counts as “no change”.
 *
 * Focused logged-metric editing uses a separate full-decimal string; save logic lives in
 * `experiment-details-view.tsx`. Guide: `/docs/reference/metric-display-formatting`.
 */

/**
 * If two values differ by less than this (absolute), the UI treats them as **equal** for
 * **comparison** UI only (not API or storage).
 *
 * **Formatting / UX effect:** very small parent–child gaps show as **no real change** (signed delta
 * string **`+0`** from `formatMetricSignedDeltaForDisplay`, equality icon in `MetricDeltaVsParent`),
 * and “better / worse” coloring vs parent is turned off so float noise does not flicker arrows.
 *
 * **Turn it up** → more pairs count as equal → calmer DAG/sidebar. **Turn it down** → smaller
 * differences count as real → more arrows and color, more noise.
 *
 * Independent of how many **digits** you show (`METRIC_DISPLAY_AUTO_FORMAT_PRECISION`).
 *
 * **Examples** (with default `1e-10`):
 * - Signed delta `5e-11` → formatted as **`+0`** (tie).
 * - Signed delta `5e-9` → non-zero signed delta string.
 * - Parent `1`, child `1 + 5e-11`, maximize → no better/worse hint.
 * - Parent `1`, child `1 + 5e-9`, maximize → gap large enough for better/worse.
 */
export const METRIC_DISPLAY_TIE_EPSILON = 1e-10;

/**
 * Caps how many **significant figures** appear in the formatted text (not “decimals after the
 * point”: `100` and `0.0123` share the same digit budget).
 *
 * **Formatting effect:** higher → longer strings, more detail in cells and labels; lower → shorter,
 * rounder numbers everywhere this formatter runs (read-only metrics, blurred logged value, delta
 * magnitudes).
 *
 * Override in code/tests via `formatValue(..., { precision })` or
 * `MetricValueDisplayFormatter` with `autoFormatPrecision`.
 *
 * **Examples** (same input `0.012312312312312312`, exponent bound `6`; only precision changes):
 * - `4` → `"0.01231"`
 * - `7` (default) → `"0.01231231"`
 * - `10` → `"0.01231231231"`
 */
export const METRIC_DISPLAY_AUTO_FORMAT_PRECISION = 7;

/**
 * How far from “normal” scale a number can get before the UI prefers **scientific** form (`1e-7`,
 * `1e+7`) instead of many leading zeros or very long integers.
 *
 * **Formatting effect:** higher bound → more values stay as plain `0.000…01` or `10000000`;
 * lower bound → scientific notation appears sooner → shorter strings in tight layouts.
 *
 * Does **not** apply to the logged-metric **focused** full-decimal display.
 *
 * **Examples** (precision `7`; only exponent bound changes):
 * - Input `1e-6`: bound `4` → `"1e-6"`; bound `6` (default) → `"0.000001"`.
 * - Input `1e-8`: bound `6` → `"1e-8"`; bound `9` → `"0.00000001"`.
 * - Input `100000`: bound `4` → `"1e+5"`; bound `6` → `"100000"`.
 * - Input `1e7`: bound `6` → `"1e+7"`; bound `9` → `"10000000"`.
 */
export const METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND = 6;
