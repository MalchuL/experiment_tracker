import { describe, expect, it } from "vitest";
import { applySmoothing } from "./smoothing";

describe("applySmoothing", () => {
  it("returns original data when weight is zero", () => {
    const data = [1, 2, "nan", "inf"] as const;
    expect(applySmoothing([...data], 0)).toEqual([...data]);
  });

  it("skips non-finite values but preserves them in output", () => {
    const result = applySmoothing([1, "nan", 3, "-inf", 5], 0.5);
    expect(result[1]).toBe("nan");
    expect(result[3]).toBe("-inf");
    expect(result[0]).toBe(1);
    expect(result[2]).toBe(2);
    expect(result[4]).toBe(3.5);
  });
});
