import type { ScalarValueKind, ScalarWireValue } from "@/domain/scalars/types";
import {
  classifyScalarValue,
  plotlySymbolForScalarKind,
} from "@/domain/scalars/utils/scalar-value";

export type ScalarPlotMarkerRole = "before" | "after";

export interface ScalarPlotPoint {
  step: number;
  value: ScalarWireValue;
}

export interface ScalarPlotMarker {
  step: number;
  y: number;
  kind: Exclude<ScalarValueKind, "finite">;
  role: ScalarPlotMarkerRole;
}

export interface ScalarPlotLineSeries {
  x: number[];
  y: Array<number | null>;
}

export interface ScalarPlotSeries {
  line: ScalarPlotLineSeries;
  markers: ScalarPlotMarker[];
}

interface LastFinitePoint {
  step: number;
  value: number;
}

export function buildScalarPlotSeries(points: ScalarPlotPoint[]): ScalarPlotSeries {
  const sorted = [...points].sort((a, b) => a.step - b.step);
  const lineX: number[] = [];
  const lineY: Array<number | null> = [];
  const markers: ScalarPlotMarker[] = [];

  let lastFinite: LastFinitePoint | null = null;
  let activeNonFiniteKind: Exclude<ScalarValueKind, "finite"> | null = null;
  let beforeMarkerPlaced = false;

  for (const point of sorted) {
    const kind = classifyScalarValue(point.value);
    if (kind !== "finite") {
      if (lastFinite && !beforeMarkerPlaced) {
        markers.push({
          step: lastFinite.step,
          y: lastFinite.value,
          kind,
          role: "before",
        });
        beforeMarkerPlaced = true;
      }
      activeNonFiniteKind = kind;
      if (lineX.length > 0) {
        lineX.push(point.step);
        lineY.push(null);
      }
      continue;
    }

    const finiteValue = point.value;
    if (activeNonFiniteKind) {
      markers.push({
        step: point.step,
        y: finiteValue,
        kind: activeNonFiniteKind,
        role: "after",
      });
      activeNonFiniteKind = null;
      beforeMarkerPlaced = false;
    }

    lineX.push(point.step);
    lineY.push(finiteValue);
    lastFinite = { step: point.step, value: finiteValue };
  }

  return { line: { x: lineX, y: lineY }, markers };
}

export function markerSymbolForScalarMarker(marker: ScalarPlotMarker): string {
  return plotlySymbolForScalarKind(marker.kind);
}
