import { describe, expect, it } from "vitest";
import { decodeStringSelection, encodeStringSelection } from "./selection-codec";

describe("selection codec", () => {
  it("roundtrips slash-prefixed metric and artifact ids", () => {
    const values = ["train/loss", "val/accuracy", "image:train/sample"];
    const encoded = encodeStringSelection(values);
    expect(decodeStringSelection(encoded)).toEqual(values);
  });

  it("deduplicates values while encoding", () => {
    const encoded = encodeStringSelection(["train/loss", "train/loss", "loss"]);
    expect(decodeStringSelection(encoded)).toEqual(["train/loss", "loss"]);
  });
});
