import { describe, expect, it } from "vitest";
import { buildHparamsCompareRows, flattenHparams } from "./hparams-compare";

describe("hparams comparison utilities", () => {
  it("flattens nested objects and arrays into canonical paths", () => {
    expect(
      flattenHparams({ model: { layers: [64, 128] }, empty: {} }).map((row) => row.pathKey)
    ).toEqual(["empty", "model.layers[0]", "model.layers[1]"]);
  });

  it("builds rows in canonical path order", () => {
    const rows = buildHparamsCompareRows([
      { hparams: { lr: 0.1, removed: true, same: "x" } },
      { hparams: { lr: 0.2, added: 5, same: "x" } },
    ]);

    expect(rows.map((row) => row.pathKey)).toEqual(["added", "lr", "removed", "same"]);
    expect(rows.find((row) => row.pathKey === "lr")?.values).toEqual([0.1, 0.2]);
    expect(rows.find((row) => row.pathKey === "removed")?.values).toEqual([true, undefined]);
  });
});
