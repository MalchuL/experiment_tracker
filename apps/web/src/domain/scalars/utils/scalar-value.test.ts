import { describe, expect, it } from "vitest";

import {
  classifyScalarValue,
  formatScalarWireForDisplay,
  isFiniteScalarValue,
  plotlySymbolForScalarKind,
} from "@/domain/scalars/utils/scalar-value";

describe("scalar-value", () => {
  it("classifies wire sentinels and native non-finite numbers", () => {
    expect(classifyScalarValue("nan")).toBe("nan");
    expect(classifyScalarValue("inf")).toBe("inf");
    expect(classifyScalarValue("-inf")).toBe("-inf");
    expect(classifyScalarValue(Number.NaN)).toBe("nan");
    expect(classifyScalarValue(Number.POSITIVE_INFINITY)).toBe("inf");
    expect(classifyScalarValue(Number.NEGATIVE_INFINITY)).toBe("-inf");
    expect(classifyScalarValue(0.5)).toBe("finite");
  });

  it("formats non-finite values for display", () => {
    expect(formatScalarWireForDisplay("nan")).toBe("NaN");
    expect(formatScalarWireForDisplay("inf")).toBe("∞");
    expect(formatScalarWireForDisplay("-inf")).toBe("-∞");
    expect(formatScalarWireForDisplay(1)).toBe("1");
  });

  it("maps kinds to Plotly symbols", () => {
    expect(plotlySymbolForScalarKind("inf")).toBe("triangle-up");
    expect(plotlySymbolForScalarKind("nan")).toBe("square");
    expect(plotlySymbolForScalarKind("-inf")).toBe("triangle-down");
  });

  it("detects finite values", () => {
    expect(isFiniteScalarValue(0.25)).toBe(true);
    expect(isFiniteScalarValue("nan")).toBe(false);
  });
});
