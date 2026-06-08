import { describe, expect, it } from "vitest";
import { parseHparamsJson } from "./hparams-json";

describe("hparams JSON utilities", () => {
  it("requires a top-level JSON object", () => {
    expect(() => parseHparamsJson("[]")).toThrow("must be a JSON object");
    expect(parseHparamsJson('{"optimizer":{"lr":0.1}}')).toEqual({
      optimizer: { lr: 0.1 },
    });
  });

});
