import { describe, expect, it } from "vitest";
import { displayHparamsValue, hparamsValueClassName } from "./hparams-display";

describe("hparams-display", () => {
  it("formats primitive values like the sidebar tree", () => {
    expect(displayHparamsValue(128)).toBe("128");
    expect(displayHparamsValue(false)).toBe("false");
    expect(displayHparamsValue("dev")).toBe('"dev"');
    expect(displayHparamsValue([55000, 5000, 10000])).toBe("[55000, 5000, 10000]");
  });

  it("assigns type-based color classes", () => {
    expect(hparamsValueClassName(1)).toContain("blue");
    expect(hparamsValueClassName(true)).toContain("violet");
    expect(hparamsValueClassName("x")).toContain("emerald");
    expect(hparamsValueClassName(null)).toContain("italic");
  });
});
