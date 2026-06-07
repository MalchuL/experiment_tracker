import { describe, expect, it } from "vitest";
import {
  applyYRangeToChartData,
  computeAutoYBounds,
  computeUniformYTicks,
  resolveComparePlotYDomain,
} from "./compute-plot-chart-layout";
import type { MetricsPlotChartPoint } from "./build-metrics-plot-data";

describe("computeAutoYBounds", () => {
  it("returns [0, 1] for empty values", () => {
    expect(computeAutoYBounds([])).toEqual([0, 1]);
  });

  it("pads a single value", () => {
    const [min, max] = computeAutoYBounds([5]);
    expect(min).toBeLessThan(5);
    expect(max).toBeGreaterThan(5);
  });

  it("adds padding around a range", () => {
    const [min, max] = computeAutoYBounds([0, 100]);
    expect(min).toBeLessThan(0);
    expect(max).toBeGreaterThan(100);
  });
});

describe("resolveComparePlotYDomain", () => {
  const values = [10, 20, 30];

  it("auto-computes both bounds when unset", () => {
    const result = resolveComparePlotYDomain({ yMin: null, yMax: null, values });
    expect(result.yMin).toBeNull();
    expect(result.yMax).toBeNull();
    expect(result.domain[0]).toBeLessThan(10);
    expect(result.domain[1]).toBeGreaterThan(30);
  });

  it("auto-computes ymax when only ymin is set", () => {
    const result = resolveComparePlotYDomain({ yMin: 5, yMax: null, values });
    expect(result.yMin).toBe(5);
    expect(result.yMax).toBeNull();
    expect(result.domain[0]).toBe(5);
    expect(result.domain[1]).toBeGreaterThan(30);
  });

  it("auto-computes ymin when only ymax is set", () => {
    const result = resolveComparePlotYDomain({ yMin: null, yMax: 40, values });
    expect(result.yMin).toBeNull();
    expect(result.yMax).toBe(40);
    expect(result.domain[1]).toBe(40);
    expect(result.domain[0]).toBeLessThan(10);
  });

  it("bumps ymax when ymin exceeds ymax and min was edited", () => {
    const result = resolveComparePlotYDomain({
      yMin: 50,
      yMax: 10,
      values,
      lastEdited: "min",
    });
    expect(result.domain).toEqual([50, 51]);
    expect(result.yMin).toBe(50);
    expect(result.yMax).toBe(10);
  });

  it("lowers ymin when ymax is below ymin and max was edited", () => {
    const result = resolveComparePlotYDomain({
      yMin: 50,
      yMax: 10,
      values,
      lastEdited: "max",
    });
    expect(result.domain).toEqual([9, 10]);
    expect(result.yMin).toBe(50);
    expect(result.yMax).toBe(10);
  });

  it("defaults to bumping ymax when bounds conflict without lastEdited", () => {
    const result = resolveComparePlotYDomain({ yMin: 25, yMax: 5, values });
    expect(result.domain).toEqual([25, 26]);
  });
});

describe("computeUniformYTicks", () => {
  it("spaces ticks evenly from min to max", () => {
    const ticks = computeUniformYTicks([0, 0.5], 4);
    expect(ticks).toHaveLength(4);
    expect(ticks[0]).toBe(0);
    expect(ticks[3]).toBe(0.5);
    const step = 0.5 / 3;
    expect(ticks[1]).toBeCloseTo(step, 10);
    expect(ticks[2]).toBeCloseTo(step * 2, 10);
    expect(ticks[1]! - ticks[0]!).toBeCloseTo(ticks[2]! - ticks[1]!, 10);
    expect(ticks[2]! - ticks[1]!).toBeCloseTo(ticks[3]! - ticks[2]!, 10);
  });

  it("returns a single tick when min equals max", () => {
    expect(computeUniformYTicks([2, 2], 5)).toEqual([2]);
  });
});

describe("applyYRangeToChartData", () => {
  const chartData: MetricsPlotChartPoint[] = [
    { experimentName: "a", experimentId: "1", s1: 5, s2: 15 },
    { experimentName: "b", experimentId: "2", s1: 25, s2: null },
  ];

  it("nulls values outside the domain", () => {
    const filtered = applyYRangeToChartData(chartData, ["s1", "s2"], [10, 20]);
    expect(filtered[0]?.s1).toBeNull();
    expect(filtered[0]?.s2).toBe(15);
    expect(filtered[1]?.s1).toBeNull();
    expect(filtered[1]?.s2).toBeNull();
  });

  it("keeps values inside the domain", () => {
    const filtered = applyYRangeToChartData(chartData, ["s1", "s2"], [0, 30]);
    expect(filtered[0]?.s1).toBe(5);
    expect(filtered[0]?.s2).toBe(15);
    expect(filtered[1]?.s1).toBe(25);
  });
});
