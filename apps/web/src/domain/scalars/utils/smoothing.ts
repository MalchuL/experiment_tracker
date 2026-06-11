import type { ScalarWireValue } from "@/domain/scalars/types";
import { isFiniteScalarValue } from "@/domain/scalars/utils/scalar-value";

export function applySmoothing(data: ScalarWireValue[], weight: number): ScalarWireValue[] {
  if (weight === 0 || data.length === 0) return data;
  const smoothed: ScalarWireValue[] = [];
  let lastFinite: number | null = null;
  for (const value of data) {
    if (!isFiniteScalarValue(value)) {
      smoothed.push(value);
      continue;
    }
    if (lastFinite === null) {
      smoothed.push(value);
      lastFinite = value;
      continue;
    }
    const smoothedValue = lastFinite * weight + value * (1 - weight);
    smoothed.push(smoothedValue);
    lastFinite = smoothedValue;
  }
  return smoothed;
}
