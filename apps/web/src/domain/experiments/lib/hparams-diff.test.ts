import { describe, expect, it } from "vitest";
import { summarizeHparamsDiff } from "./hparams-diff";

describe("experiment hparams diff summary", () => {
  it("counts nested additions, removals, and changes against the parent", () => {
    expect(
      summarizeHparamsDiff(
        { optimizer: { lr: 0.1, momentum: 0.9 }, removed: true },
        { optimizer: { lr: 0.2, momentum: 0.9 }, added: [1, 2] }
      )
    ).toEqual({ added: 2, removed: 1, changed: 1 });
  });

  it("counts every parent leaf as removed when the current document is absent", () => {
    expect(summarizeHparamsDiff({ model: { width: 128 }, enabled: true }, null)).toEqual({
      added: 0,
      removed: 2,
      changed: 0,
    });
  });
});
