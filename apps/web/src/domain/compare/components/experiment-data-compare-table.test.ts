import { describe, expect, it } from "vitest";
import { classifyExperimentDataRow } from "./experiment-data-compare-table";

const key = (value: number) => String(value);

describe("classifyExperimentDataRow", () => {
  it("compares every column with the baseline", () => {
    expect(classifyExperimentDataRow([1, 2, 2, undefined], "baseline", key)).toEqual([
      "unchanged",
      "changed",
      "changed",
      "removed",
    ]);
  });

  it("compares every column with its previous column", () => {
    expect(classifyExperimentDataRow([1, 2, 2, undefined, 3], "previous", key)).toEqual([
      "unchanged",
      "changed",
      "unchanged",
      "removed",
      "added",
    ]);
  });
});
