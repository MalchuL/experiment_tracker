import type { ScalarValueKind, ScalarWireValue } from "@/domain/scalars/types";

export function classifyScalarValue(value: ScalarWireValue): ScalarValueKind {
  if (typeof value === "string") {
    return value;
  }
  if (Number.isNaN(value)) {
    return "nan";
  }
  if (value === Number.POSITIVE_INFINITY) {
    return "inf";
  }
  if (value === Number.NEGATIVE_INFINITY) {
    return "-inf";
  }
  return "finite";
}

export function isFiniteScalarValue(value: ScalarWireValue): value is number {
  return classifyScalarValue(value) === "finite";
}

export function formatScalarWireForDisplay(value: ScalarWireValue): string {
  const kind = classifyScalarValue(value);
  if (kind === "nan") {
    return "NaN";
  }
  if (kind === "inf") {
    return "∞";
  }
  if (kind === "-inf") {
    return "-∞";
  }
  if (!isFiniteScalarValue(value)) {
    return String(value);
  }
  return Number.isInteger(value) ? String(value) : value.toPrecision(6);
}

export function plotlySymbolForScalarKind(
  kind: Exclude<ScalarValueKind, "finite">
): "triangle-up" | "square" | "triangle-down" {
  if (kind === "inf") {
    return "triangle-up";
  }
  if (kind === "-inf") {
    return "triangle-down";
  }
  return "square";
}
