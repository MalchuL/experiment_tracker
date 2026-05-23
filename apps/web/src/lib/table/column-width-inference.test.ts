import { describe, expect, it } from "vitest";
import { inferMetricColumnWidthPx } from "./column-width-inference";

describe("inferMetricColumnWidthPx", () => {
  it("uses the minimum for short headers and compact values", () => {
    expect(
      inferMetricColumnWidthPx({
        header: "acc",
        values: [1, 0.5],
        minPx: 72,
        maxPx: 260,
      })
    ).toBe(72);
  });

  it("expands for longer metric names", () => {
    const width = inferMetricColumnWidthPx({
      header: "validation/epoch_weighted_accuracy",
      values: [0.92],
      minPx: 72,
      maxPx: 260,
    });
    expect(width).toBeGreaterThan(72);
    expect(width).toBeLessThanOrEqual(260);
  });

  it("expands for long formatted values", () => {
    const width = inferMetricColumnWidthPx({
      header: "loss",
      values: [1001011.123456],
      minPx: 72,
      maxPx: 260,
    });
    expect(width).toBeGreaterThan(72);
  });

  it("clamps very long headers and values to the maximum", () => {
    expect(
      inferMetricColumnWidthPx({
        header: "very/long/metric/name/that/should/not/own/the/whole/table",
        values: [12345678901234567890],
        minPx: 72,
        maxPx: 180,
      })
    ).toBe(180);
  });
});
