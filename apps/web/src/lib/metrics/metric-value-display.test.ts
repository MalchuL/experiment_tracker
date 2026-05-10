import { describe, expect, it } from "vitest";
import {
  formatMetricScalarForDisplay,
  formatMetricScalarForEditorDraft,
  formatMetricScalarForEditorFull,
  formatMetricSignedDeltaForDisplay,
  metricEditorValuesEffectivelyEqual,
  metricIsBetterThanParent,
} from "./metric-value-display";
import { METRIC_DISPLAY_EXPONENTIAL_FRACTION_DIGITS } from "@/lib/constants/metric-display";

describe("formatMetricScalarForDisplay", () => {
  it("uses short exponential for long-decimal floats (no 16-digit mantissa)", () => {
    const v = 0.012312312312312312;
    const s = formatMetricScalarForDisplay(v);
    expect(s).toMatch(/e[+-]\d+$/i);
    expect(s.length).toBeLessThanOrEqual(14);
    expect(s).not.toMatch(/1\.231231231231231/);
    const lower = s.toLowerCase();
    const expIdx = lower.indexOf("e");
    expect(expIdx).toBeGreaterThan(0);
    const mantissa = s.slice(0, expIdx).replace(/^-/, "");
    const frac = mantissa.includes(".") ? mantissa.split(".")[1]! : "";
    expect(frac.length).toBeLessThanOrEqual(METRIC_DISPLAY_EXPONENTIAL_FRACTION_DIGITS);
  });

  it("uses fixed form for compact decimals without padding zeros", () => {
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

  it("uses exponential for tiny positive where toFixed rounds to zero", () => {
    const s = formatMetricScalarForDisplay(1e-12);
    expect(s).toMatch(/e-/);
  });
});

describe("formatMetricScalarForEditorDraft", () => {
  it("matches display exponential digit budget (not bare toExponential())", () => {
    const v = 0.012312312312312312;
    const s = formatMetricScalarForEditorDraft(v);
    expect(s).toMatch(/e[+-]\d+$/i);
    expect(s).not.toMatch(/1\.231231231231231/);
    expect(s.length).toBeLessThanOrEqual(14);
  });

  it("preserves sign for negative exponential", () => {
    const s = formatMetricScalarForEditorDraft(-0.012312312312312312);
    expect(s.startsWith("-")).toBe(true);
    expect(s.slice(1)).toMatch(/e[+-]\d+$/i);
  });

  it("uses fixed when raw string is short (no trailing zero padding)", () => {
    expect(formatMetricScalarForEditorDraft(0.05)).toBe("0.05");
    expect(formatMetricScalarForEditorDraft(1)).toBe("1");
  });
});

describe("formatMetricScalarForEditorFull", () => {
  it("returns plain String(number) when not in scientific form", () => {
    const v = 0.012312312312312312;
    expect(formatMetricScalarForEditorFull(v)).toBe(String(v));
    expect(formatMetricScalarForEditorFull(v)).not.toMatch(/e[+-]/i);
  });

  it("expands scientific String(number) to decimal when locale can represent it", () => {
    expect(formatMetricScalarForEditorFull(1e-7)).toBe("0.0000001");
  });

  it("keeps scientific notation when expansion would round to zero", () => {
    const s = formatMetricScalarForEditorFull(1e-21);
    expect(s).toMatch(/e-/i);
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
  it("returns 0 for tie band", () => {
    expect(formatMetricSignedDeltaForDisplay(0)).toBe("0");
    expect(formatMetricSignedDeltaForDisplay(5e-11)).toBe("0");
  });

  it("prefixes sign and uses bounded exponential for long decimals", () => {
    const d = 0.012312312312312312 - 0.01;
    const s = formatMetricSignedDeltaForDisplay(d);
    expect(s[0] === "+" || s[0] === "-").toBe(true);
    expect(s.slice(1)).toMatch(/e[+-]\d+$/i);
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
