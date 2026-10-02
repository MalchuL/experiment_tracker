import { expect, it } from "vitest";
import { scalarPage, scalarPageSize } from "./scalar-pagination";
it("clamps pages and validates page sizes", () => {
  expect(scalarPage(9, 25, 12)).toBe(3);
  expect(scalarPage(-1, 0, 12)).toBe(1);
  expect(scalarPage(Number.NaN, 20, 12)).toBe(1);
  expect(scalarPageSize(24)).toBe(24);
  expect(scalarPageSize(0)).toBe(12);
});
