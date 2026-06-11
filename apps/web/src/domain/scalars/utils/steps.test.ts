import { describe, expect, it } from "vitest";
import { closestStep } from "./steps";

describe("closestStep", () => {
  it("returns null for empty step lists", () => {
    expect(closestStep(10, [])).toBeNull();
  });

  it("picks the nearest available step", () => {
    expect(closestStep(7, [1, 5, 10, 20])).toBe(5);
    expect(closestStep(9, [1, 5, 10, 20])).toBe(10);
  });

  it("keeps the first step on equal distance ties", () => {
    expect(closestStep(15, [10, 20])).toBe(10);
  });
});
