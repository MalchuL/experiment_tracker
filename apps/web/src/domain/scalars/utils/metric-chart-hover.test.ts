import { describe, expect, it } from "vitest";

import {
  buildExperimentHoverDisplayNames,
  dedupeHoverRowsByExperimentAndStep,
  filterHoverRowsToVisibleYRange,
  getNextScalarHoverMode,
  isScalarYInVisibleRange,
  resolveHoverYRangeFromEvent,
  truncateExperimentHoverName,
  usesUnifiedMultiHover,
} from "@/domain/scalars/utils/metric-chart-hover";

describe("metric-chart-hover", () => {
  it("truncates long experiment names", () => {
    expect(truncateExperimentHoverName("abcdefghij", 5)).toBe("abcd…");
    expect(truncateExperimentHoverName("abc", 5)).toBe("abc");
  });

  it("builds truncated hover labels keyed by experiment id", () => {
    const labels = buildExperimentHoverDisplayNames(
      [
        { id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", name: "run-1" },
        { id: "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj", name: "run-1" },
        { id: "11111111-2222-3333-4444-555555555555", name: "unique" },
      ],
      50
    );

    expect(labels.get("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")).toBe("run-1");
    expect(labels.get("ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj")).toBe("run-1");
    expect(labels.get("11111111-2222-3333-4444-555555555555")).toBe("unique");
  });

  it("dedupes hover rows by experiment id and step", () => {
    const rows = dedupeHoverRowsByExperimentAndStep([
      { experimentId: "a", step: 1, value: 0.1 },
      { experimentId: "a", step: 1, value: 0.2 },
      { experimentId: "b", step: 1, value: 0.3 },
    ]);

    expect(rows).toEqual([
      { experimentId: "a", step: 1, value: 0.1 },
      { experimentId: "b", step: 1, value: 0.3 },
    ]);
  });

  it("detects unified multi-hover modes", () => {
    expect(usesUnifiedMultiHover("compare")).toBe(true);
    expect(usesUnifiedMultiHover("visible")).toBe(true);
    expect(usesUnifiedMultiHover("nearest")).toBe(false);
  });

  it("filters hover rows to the visible y-axis range", () => {
    const rows = [
      { experimentId: "a", step: 1, sortValue: 0.2 },
      { experimentId: "b", step: 1, sortValue: 0.8 },
    ];

    expect(filterHoverRowsToVisibleYRange(rows, [0, 0.5])).toEqual([rows[0]]);
    expect(filterHoverRowsToVisibleYRange(rows, null)).toEqual(rows);
    expect(isScalarYInVisibleRange(0.5, [1, 0])).toBe(true);
  });

  it("prefers live plotly y-axis range over stored domain", () => {
    expect(
      resolveHoverYRangeFromEvent(
        [{ yaxis: { range: [0.1, 0.9] } }],
        [0, 1]
      )
    ).toEqual([0.1, 0.9]);
    expect(resolveHoverYRangeFromEvent([], [0.2, 0.7])).toEqual([0.2, 0.7]);
    expect(resolveHoverYRangeFromEvent([], null)).toBeNull();
  });

  it("cycles hover modes through compare, visible, and nearest", () => {
    expect(getNextScalarHoverMode("compare")).toBe("visible");
    expect(getNextScalarHoverMode("visible")).toBe("nearest");
    expect(getNextScalarHoverMode("nearest")).toBe("compare");
  });
});
