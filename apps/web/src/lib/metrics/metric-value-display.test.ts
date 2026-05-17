import { describe, expect, it } from "vitest";
import {
  MetricValueDisplayFormatter,
  formatMetricScalarForDisplay,
  formatMetricScalarForEditorDraft,
  formatMetricScalarForEditorFull,
  formatMetricScalarTooltipFull,
  formatMetricSignedDeltaForDisplay,
  metricEditorValuesEffectivelyEqual,
  metricIsBetterThanParent,
  metricSignedDeltaIsDisplayTie,
} from "./metric-value-display";

describe("MetricValueDisplayFormatter", () => {
  it("uses constructor overrides without affecting default exported functions", () => {
    const lowPrec = new MetricValueDisplayFormatter({ autoFormatPrecision: 2 });
    expect(lowPrec.formatScalarForDisplay(12.34)).toBe("12");
    expect(formatMetricScalarForDisplay(12.34)).toBe("12.34");
  });
});

describe("formatMetricScalarForDisplay", () => {
  it("uses mathjs auto format for long decimals (significant digits, not raw exponential)", () => {
    const v = 0.012312312312312312;
    expect(formatMetricScalarForDisplay(v)).toBe("0.01231231");
  });

  it("uses compact plain form for typical magnitudes", () => {
    expect(formatMetricScalarForDisplay(0.05)).toBe("0.05");
    expect(formatMetricScalarForDisplay(1)).toBe("1");
    expect(formatMetricScalarForDisplay(42)).toBe("42");
    expect(formatMetricScalarForDisplay(100)).toBe("100");
    expect(formatMetricScalarForDisplay(9999)).toBe("9999");
  });

  it("returns em dash for nullish or non-finite", () => {
    expect(formatMetricScalarForDisplay(null)).toBe("—");
    expect(formatMetricScalarForDisplay(undefined)).toBe("—");
    expect(formatMetricScalarForDisplay(Number.NaN)).toBe("—");
  });

  it("formats zero", () => {
    expect(formatMetricScalarForDisplay(0)).toBe("0");
  });

  it("uses exponential for tiny magnitudes outside auto exponent band", () => {
    expect(formatMetricScalarForDisplay(1e-12)).toBe("1e-12");
  });
});

describe("formatMetricScalarForEditorDraft", () => {
  it("matches display auto-format for long decimals", () => {
    const v = 0.012312312312312312;
    expect(formatMetricScalarForEditorDraft(v)).toBe("0.01231231");
  });

  it("preserves sign for negative values", () => {
    expect(formatMetricScalarForEditorDraft(-0.012312312312312312)).toBe("-0.01231231");
  });

  it("matches display for compact values", () => {
    expect(formatMetricScalarForEditorDraft(0.05)).toBe("0.05");
    expect(formatMetricScalarForEditorDraft(1)).toBe("1");
  });
});

describe("formatMetricScalarForEditorFull", () => {
  it("keeps full double decimal digits (draft may round)", () => {
    const v = 0.012312312312312312;
    expect(formatMetricScalarForEditorDraft(v)).toBe("0.01231231");
    expect(formatMetricScalarForEditorFull(v)).toBe("0.012312312312312312");
  });

  it("uses plain decimals, not exponential, for tiny magnitudes", () => {
    expect(formatMetricScalarForEditorDraft(1e-7)).toBe("1e-7");
    expect(formatMetricScalarForEditorFull(1e-7)).toBe("0.0000001");
    expect(formatMetricScalarForEditorDraft(1e-21)).toBe("1e-21");
    expect(formatMetricScalarForEditorFull(1e-21)).toBe("0.000000000000000000001");
  });
});

describe("formatMetricScalarTooltipFull", () => {
  it("matches editor full for finite numbers", () => {
    const v = 0.012312312312312312;
    expect(formatMetricScalarTooltipFull(v)).toBe(formatMetricScalarForEditorFull(v));
  });

  it("returns em dash for nullish or non-finite", () => {
    expect(formatMetricScalarTooltipFull(null)).toBe("—");
    expect(formatMetricScalarTooltipFull(undefined)).toBe("—");
    expect(formatMetricScalarTooltipFull(Number.NaN)).toBe("—");
  });
});

describe("metricEditorValuesEffectivelyEqual", () => {
  it("treats identical and bitwise-equal as unchanged", () => {
    expect(metricEditorValuesEffectivelyEqual(1.5, 1.5)).toBe(true);
    expect(metricEditorValuesEffectivelyEqual(0, 0)).toBe(true);
  });

  it("treats tiny float drift as unchanged", () => {
    const x = 0.1 + 0.2;
    expect(metricEditorValuesEffectivelyEqual(x, 0.3)).toBe(true);
  });

  it("detects meaningful changes", () => {
    expect(metricEditorValuesEffectivelyEqual(1, 1.00001)).toBe(false);
    expect(metricEditorValuesEffectivelyEqual(0, 1e-6)).toBe(false);
  });
});

describe("formatMetricSignedDeltaForDisplay", () => {
  it("returns +0 for tie band", () => {
    expect(formatMetricSignedDeltaForDisplay(0)).toBe("+0");
    expect(formatMetricSignedDeltaForDisplay(5e-11)).toBe("+0");
  });

  it("prefixes sign and formats magnitude with formatValue", () => {
    const d = 0.012312312312312312 - 0.01;
    const s = formatMetricSignedDeltaForDisplay(d);
    expect(s[0] === "+" || s[0] === "-").toBe(true);
    expect(s).toMatch(/^[+-]0\.002312312$/);
  });
});

describe("metricSignedDeltaIsDisplayTie", () => {
  it("matches the tie band used for +0 deltas", () => {
    expect(metricSignedDeltaIsDisplayTie(0)).toBe(true);
    expect(metricSignedDeltaIsDisplayTie(5e-11)).toBe(true);
    expect(metricSignedDeltaIsDisplayTie(5e-9)).toBe(false);
  });

  it("follows formatter tieEpsilon overrides", () => {
    const f = new MetricValueDisplayFormatter({ tieEpsilon: 1e-6 });
    expect(f.signedDeltaIsDisplayTie(1e-7)).toBe(true);
    expect(f.formatSignedDeltaForDisplay(1e-7)).toBe("+0");
    expect(metricSignedDeltaIsDisplayTie(1e-7)).toBe(false);
  });
});

describe("metricIsBetterThanParent", () => {
  it("returns null on tie", () => {
    expect(metricIsBetterThanParent(1, 1, "maximize")).toBeNull();
    expect(metricIsBetterThanParent(1, 1 + 1e-11, "maximize")).toBeNull();
  });

  it("maximize: higher is better", () => {
    expect(metricIsBetterThanParent(2, 1, "maximize")).toBe(true);
    expect(metricIsBetterThanParent(1, 2, "maximize")).toBe(false);
  });

  it("minimize: lower is better", () => {
    expect(metricIsBetterThanParent(1, 2, "minimize")).toBe(true);
    expect(metricIsBetterThanParent(2, 1, "minimize")).toBe(false);
  });

  it("returns null when value or parent missing", () => {
    expect(metricIsBetterThanParent(null, 1, "maximize")).toBeNull();
    expect(metricIsBetterThanParent(1, null, "maximize")).toBeNull();
  });
});
