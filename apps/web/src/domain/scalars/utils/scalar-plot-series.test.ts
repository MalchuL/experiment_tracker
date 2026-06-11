import { describe, expect, it } from "vitest";

import { buildScalarPlotSeries } from "@/domain/scalars/utils/scalar-plot-series";

describe("buildScalarPlotSeries", () => {
  it("keeps finite-only series as a continuous line", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: 0.5 },
      { step: 2, value: 0.25 },
    ]);
    expect(series.line).toEqual({ x: [1, 2], y: [0.5, 0.25] });
    expect(series.markers).toEqual([]);
  });

  it("places before/after markers on adjacent finite points, not on non-finite steps", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: 0.5 },
      { step: 2, value: "nan" },
      { step: 3, value: 0.25 },
      { step: 4, value: "inf" },
      { step: 5, value: 0.1 },
    ]);

    expect(series.line.x).toEqual([1, 2, 3, 4, 5]);
    expect(series.line.y).toEqual([0.5, null, 0.25, null, 0.1]);
    expect(series.markers).toEqual([
      { step: 1, y: 0.5, kind: "nan", role: "before" },
      { step: 3, y: 0.25, kind: "nan", role: "after" },
      { step: 3, y: 0.25, kind: "inf", role: "before" },
      { step: 5, y: 0.1, kind: "inf", role: "after" },
    ]);
  });

  it("uses one before/after pair for consecutive non-finite steps", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: 0.5 },
      { step: 2, value: "nan" },
      { step: 3, value: "nan" },
      { step: 4, value: 0.25 },
    ]);

    expect(series.line.x).toEqual([1, 2, 3, 4]);
    expect(series.line.y).toEqual([0.5, null, null, 0.25]);
    expect(series.markers).toEqual([
      { step: 1, y: 0.5, kind: "nan", role: "before" },
      { step: 4, y: 0.25, kind: "nan", role: "after" },
    ]);
  });

  it("omits before marker when the series starts with non-finite values", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: "nan" },
      { step: 2, value: 0.25 },
    ]);

    expect(series.line).toEqual({ x: [2], y: [0.25] });
    expect(series.markers).toEqual([{ step: 2, y: 0.25, kind: "nan", role: "after" }]);
  });

  it("omits after marker when the series ends with non-finite values", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: 0.5 },
      { step: 2, value: "-inf" },
    ]);

    expect(series.line).toEqual({ x: [1, 2], y: [0.5, null] });
    expect(series.markers).toEqual([{ step: 1, y: 0.5, kind: "-inf", role: "before" }]);
  });

  it("supports all-non-finite series with no markers or line", () => {
    const series = buildScalarPlotSeries([
      { step: 1, value: "nan" },
      { step: 2, value: "-inf" },
    ]);
    expect(series.line).toEqual({ x: [], y: [] });
    expect(series.markers).toEqual([]);
  });
});
