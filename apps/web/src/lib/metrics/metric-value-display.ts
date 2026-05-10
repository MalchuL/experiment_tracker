import {
  METRIC_DISPLAY_EXPONENTIAL_FRACTION_DIGITS,
  METRIC_DISPLAY_FIXED_DECIMAL_PLACES,
  METRIC_DISPLAY_MAX_INTEGER_DIGITS_FOR_FIXED,
  METRIC_DISPLAY_MAX_RAW_DECIMAL_STRING_LENGTH,
  METRIC_DISPLAY_TIE_EPSILON,
} from "@/lib/constants/metric-display";

export type MetricDisplayRow = {
  /** Shown label (e.g. `formatMetricLabel(name, label)` on DAG). */
  name: string;
  /** Pre-formatted scalar for UI. */
  value: string;
  /** Pre-formatted delta vs baseline, when applicable. */
  diff?: string;
  /** Meaningful when `diff` is set: better vs parent given metric direction. */
  isBetter?: boolean | null;
};

/** Prefer scientific notation based on string length and fixed-point safety. */
function metricPreferExponential(mag: number, fixed: string): boolean {
  if (mag > 0 && parseFloat(fixed) === 0) {
    return true;
  }
  if (String(mag).length > METRIC_DISPLAY_MAX_RAW_DECIMAL_STRING_LENGTH) {
    return true;
  }
  const intPart = fixed.split(".")[0] ?? "";
  if (intPart.length > METRIC_DISPLAY_MAX_INTEGER_DIGITS_FOR_FIXED) {
    return true;
  }
  return false;
}

function formatPositiveMagnitudeExponential(mag: number): string {
  return mag.toExponential(METRIC_DISPLAY_EXPONENTIAL_FRACTION_DIGITS);
}

/** Strip trailing fraction zeros from a `toFixed` string so `1.000000` → `1`, `0.050000` → `0.05`. */
function trimInsignificantFractionZeros(fixedPoint: string): string {
  if (!fixedPoint.includes(".")) return fixedPoint;
  return fixedPoint.replace(/\.?0+$/, "");
}

function formatPositiveMagnitude(mag: number): string {
  if (mag === 0) return "0";
  const fixed = mag.toFixed(METRIC_DISPLAY_FIXED_DECIMAL_PLACES);
  if (metricPreferExponential(mag, fixed)) {
    return formatPositiveMagnitudeExponential(mag);
  }
  return trimInsignificantFractionZeros(fixed);
}

/**
 * Text for logged-metric **value** `<Input>` when syncing from server data (blurred).
 * Uses the same length / `toFixed` rules as read-only display, then drops trailing fraction
 * zeros (`1` not `1.000000`).
 */
export function formatMetricScalarForEditorDraft(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return "0";
  const body = formatPositiveMagnitude(Math.abs(value));
  return value < 0 ? "-" + body : body;
}

/**
 * Full-precision text when the user focuses the metric value field (so they can edit the
 * underlying number, not the shortened exponential / digit-budget draft).
 *
 * Uses `String(number)` when it is already a plain decimal. If the engine uses scientific
 * notation, expands with `toLocaleString` when that does not round away subnormal values;
 * otherwise keeps the scientific string (still exact for the double).
 */
export function formatMetricScalarForEditorFull(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return Object.is(value, -0) ? "-0" : "0";
  const raw = String(value);
  if (!/[eE]/.test(raw)) return raw;
  const expanded = value.toLocaleString("en-US", {
    useGrouping: false,
    maximumFractionDigits: 20,
  });
  if (value !== 0 && (expanded === "0" || expanded === "-0")) {
    return raw;
  }
  return expanded;
}

/**
 * True when the parsed editor value should be treated as unchanged vs the stored metric
 * (skip HTTP upsert). Uses a small absolute floor and a ULP-scaled tolerance so harmless
 * float noise does not trigger saves.
 */
export function metricEditorValuesEffectivelyEqual(parsed: number, previous: number): boolean {
  if (Object.is(parsed, previous)) return true;
  if (!Number.isFinite(parsed) || !Number.isFinite(previous)) return false;
  const d = Math.abs(parsed - previous);
  const mag = Math.max(Math.abs(parsed), Math.abs(previous));
  const relativeTol = mag * Number.EPSILON * 16;
  const absoluteTol = 1e-12;
  return d <= Math.max(relativeTol, absoluteTol);
}

/** Table cells, DAG nodes, sidebar: null/empty and non-finite → em dash. */
export function formatMetricScalarForDisplay(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (!Number.isFinite(value)) return "—";
  if (value === 0) return "0";
  const sign = value < 0 ? "-" : "";
  return sign + formatPositiveMagnitude(Math.abs(value));
}

/**
 * Signed delta vs parent for DAG / sidebar. Tie (|delta| < {@link METRIC_DISPLAY_TIE_EPSILON}) → `"0"`.
 * Uses the same length-based exponential rule as {@link formatMetricScalarForDisplay} on |delta|.
 */
export function formatMetricSignedDeltaForDisplay(delta: number): string {
  if (!Number.isFinite(delta)) return "—";
  if (Math.abs(delta) < METRIC_DISPLAY_TIE_EPSILON) return "0";
  const sign = delta > 0 ? "+" : "-";
  return sign + formatPositiveMagnitude(Math.abs(delta));
}

/** Same rules as `buildMetricComparisons` in the DAG (tie band, maximize vs minimize). */
export function metricIsBetterThanParent(
  value: number | null | undefined,
  parentValue: number | null | undefined,
  direction: "maximize" | "minimize"
): boolean | null {
  if (value == null || parentValue == null) return null;
  if (!Number.isFinite(value) || !Number.isFinite(parentValue)) return null;
  if (Object.is(value, parentValue) || Math.abs(value - parentValue) < METRIC_DISPLAY_TIE_EPSILON) {
    return null;
  }
  if (direction === "maximize") return value > parentValue;
  return value < parentValue;
}

export function toMetricDisplayRow(input: {
  name: string;
  value: number | null;
  delta?: number | null;
  isBetter?: boolean | null;
}): MetricDisplayRow {
  const row: MetricDisplayRow = {
    name: input.name,
    value: formatMetricScalarForDisplay(input.value),
  };
  if (input.delta != null && Number.isFinite(input.delta)) {
    row.diff = formatMetricSignedDeltaForDisplay(input.delta);
  }
  if (input.isBetter !== undefined) {
    row.isBetter = input.isBetter;
  }
  return row;
}
