import {
  METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND,
  METRIC_DISPLAY_AUTO_FORMAT_PRECISION,
  METRIC_DISPLAY_TIE_EPSILON,
} from "@/lib/constants/metric-display";
import {
  formatValue,
  formatValueNonExponential,
  type MetricMathjsFormatOverrides,
} from "@/lib/metrics/mathjs-metric-format";

export { METRIC_FORMAT_OPTIONS, formatValue, formatValueNonExponential } from "@/lib/metrics/mathjs-metric-format";

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

/** Overrides for {@link MetricValueDisplayFormatter}; unset fields use app defaults from `metric-display` constants. */
export type MetricValueDisplayFormatOptions = {
  tieEpsilon?: number;
  autoFormatPrecision?: number;
  autoFormatExpBound?: number;
  /** Absolute tolerance in {@link MetricValueDisplayFormatter.areEditorValuesEffectivelyEqual}. */
  editorEqualAbsoluteTolerance?: number;
  /** Multiplier on `Number.EPSILON` for relative tolerance in editor equality. */
  editorEqualRelativeEpsilonMultiplier?: number;
};

type ResolvedMetricValueDisplayFormatOptions = Required<MetricValueDisplayFormatOptions>;

function resolveMetricValueDisplayFormatOptions(
  overrides?: MetricValueDisplayFormatOptions
): ResolvedMetricValueDisplayFormatOptions {
  return {
    tieEpsilon: METRIC_DISPLAY_TIE_EPSILON,
    autoFormatPrecision: METRIC_DISPLAY_AUTO_FORMAT_PRECISION,
    autoFormatExpBound: METRIC_DISPLAY_AUTO_FORMAT_EXP_BOUND,
    editorEqualAbsoluteTolerance: 1e-12,
    editorEqualRelativeEpsilonMultiplier: 16,
    ...overrides,
  };
}

/**
 * Metric scalar / delta formatting for tables, DAG, sidebar, and logged-metric editors.
 * Uses {@link formatValue} (mathjs `format`, `notation: 'auto'`).
 *
 * Use {@link metricValueDisplayFormatter} for the default app config, or `new MetricValueDisplayFormatter({ ... })` for tests or custom UIs.
 */
export class MetricValueDisplayFormatter {
  private readonly opts: ResolvedMetricValueDisplayFormatOptions;

  constructor(overrides?: MetricValueDisplayFormatOptions) {
    this.opts = resolveMetricValueDisplayFormatOptions(overrides);
  }

  private mathjsOverrides(): MetricMathjsFormatOverrides {
    return {
      precision: this.opts.autoFormatPrecision,
      expBound: this.opts.autoFormatExpBound,
    };
  }

  /** @see formatMetricScalarForDisplay */
  formatScalarForDisplay(value: number | null | undefined): string {
    if (value === null || value === undefined) return "—";
    if (!Number.isFinite(value)) return "—";
    if (value === 0) return "0";
    return formatValue(value, this.mathjsOverrides());
  }

  /** @see formatMetricScalarForEditorDraft */
  formatScalarForEditorDraft(value: number): string {
    if (!Number.isFinite(value)) return String(value);
    if (value === 0) return "0";
    return formatValue(value, this.mathjsOverrides());
  }

  /** @see formatMetricScalarForEditorFull */
  formatScalarForEditorFull(value: number): string {
    if (!Number.isFinite(value)) return String(value);
    if (value === 0) return "0";
    return formatValueNonExponential(value);
  }

  /** @see metricEditorValuesEffectivelyEqual */
  areEditorValuesEffectivelyEqual(parsed: number, previous: number): boolean {
    if (Object.is(parsed, previous)) return true;
    if (!Number.isFinite(parsed) || !Number.isFinite(previous)) return false;
    const d = Math.abs(parsed - previous);
    const mag = Math.max(Math.abs(parsed), Math.abs(previous));
    const relativeTol = mag * Number.EPSILON * this.opts.editorEqualRelativeEpsilonMultiplier;
    const absoluteTol = this.opts.editorEqualAbsoluteTolerance;
    return d <= Math.max(relativeTol, absoluteTol);
  }

  /** @see formatMetricSignedDeltaForDisplay */
  formatSignedDeltaForDisplay(delta: number): string {
    if (!Number.isFinite(delta)) return "—";
    if (Math.abs(delta) < this.opts.tieEpsilon) return "+0";
    const sign = delta > 0 ? "+" : "-";
    return sign + formatValue(Math.abs(delta), this.mathjsOverrides());
  }

  /** Same tie band as {@link formatSignedDeltaForDisplay}: absolute delta below configured tie epsilon. */
  signedDeltaIsDisplayTie(delta: number): boolean {
    if (!Number.isFinite(delta)) return false;
    return Math.abs(delta) < this.opts.tieEpsilon;
  }

  /** @see metricIsBetterThanParent */
  isBetterThanParent(
    value: number | null | undefined,
    parentValue: number | null | undefined,
    direction: "maximize" | "minimize"
  ): boolean | null {
    if (value == null || parentValue == null) return null;
    if (!Number.isFinite(value) || !Number.isFinite(parentValue)) return null;
    const eps = this.opts.tieEpsilon;
    if (Object.is(value, parentValue) || Math.abs(value - parentValue) < eps) {
      return null;
    }
    if (direction === "maximize") return value > parentValue;
    return value < parentValue;
  }

  /** @see toMetricDisplayRow */
  toDisplayRow(input: {
    name: string;
    value: number | null;
    delta?: number | null;
    isBetter?: boolean | null;
  }): MetricDisplayRow {
    const row: MetricDisplayRow = {
      name: input.name,
      value: this.formatScalarForDisplay(input.value),
    };
    if (input.delta != null && Number.isFinite(input.delta)) {
      row.diff = this.formatSignedDeltaForDisplay(input.delta);
    }
    if (input.isBetter !== undefined) {
      row.isBetter = input.isBetter;
    }
    return row;
  }
}

/** Default formatter (constants from `@/lib/constants/metric-display`). */
export const metricValueDisplayFormatter = new MetricValueDisplayFormatter();

/** Table cells, DAG nodes, sidebar: null/empty and non-finite → em dash. */
export function formatMetricScalarForDisplay(value: number | null | undefined): string {
  return metricValueDisplayFormatter.formatScalarForDisplay(value);
}

/**
 * Text for logged-metric **value** `<Input>` when syncing from server data (blurred).
 * Same mathjs auto-format as read-only display.
 */
export function formatMetricScalarForEditorDraft(value: number): string {
  return metricValueDisplayFormatter.formatScalarForEditorDraft(value);
}

/**
 * Text for the metric value field on focus — plain decimal via {@link formatValueNonExponential}
 * (never exponential `e` notation for finite values).
 */
export function formatMetricScalarForEditorFull(value: number): string {
  return metricValueDisplayFormatter.formatScalarForEditorFull(value);
}

/**
 * Full non-exponential string for read-only value tooltips (DAG, sidebar, tables).
 * Null, undefined, or non-finite → em dash (same as display cells).
 */
export function formatMetricScalarTooltipFull(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return formatMetricScalarForEditorFull(value);
}

/**
 * True when the parsed editor value should be treated as unchanged vs the stored metric
 * (skip HTTP upsert). Uses a small absolute floor and a ULP-scaled tolerance so harmless
 * float noise does not trigger saves.
 */
export function metricEditorValuesEffectivelyEqual(parsed: number, previous: number): boolean {
  return metricValueDisplayFormatter.areEditorValuesEffectivelyEqual(parsed, previous);
}

/**
 * Signed delta vs parent for DAG / sidebar. Tie (|delta| below configured tie epsilon) → **`"+0"`**
 * (explicit “no change” for deltas; use with {@link metricSignedDeltaIsDisplayTie} for icons).
 * Uses {@link formatValue} on |delta| with the same options as scalar display.
 */
export function formatMetricSignedDeltaForDisplay(delta: number): string {
  return metricValueDisplayFormatter.formatSignedDeltaForDisplay(delta);
}

/**
 * True when {@link formatMetricSignedDeltaForDisplay} would print the tie sentinel (`"+0"`).
 * Uses the same epsilon as the default formatter (override via {@link MetricValueDisplayFormatter} for tests).
 */
export function metricSignedDeltaIsDisplayTie(delta: number): boolean {
  return metricValueDisplayFormatter.signedDeltaIsDisplayTie(delta);
}

/** Same rules as `buildMetricComparisons` in the DAG (tie band, maximize vs minimize). */
export function metricIsBetterThanParent(
  value: number | null | undefined,
  parentValue: number | null | undefined,
  direction: "maximize" | "minimize"
): boolean | null {
  return metricValueDisplayFormatter.isBetterThanParent(value, parentValue, direction);
}

export function toMetricDisplayRow(input: {
  name: string;
  value: number | null;
  delta?: number | null;
  isBetter?: boolean | null;
}): MetricDisplayRow {
  return metricValueDisplayFormatter.toDisplayRow(input);
}
