import type { PlotData } from "plotly.js";
import type { MetricChartProps } from "../metric-chart";
import type { ScalarWireValue } from "../../types";
import { CHART_COLORS } from "../../constants";
import {
  buildScalarPlotSeries,
  markerSymbolForScalarMarker,
} from "../../utils/scalar-plot-series";
import { usesUnifiedMultiHover } from "../../utils/metric-chart-hover";
import {
  formatScalarWireForDisplay,
  isFiniteScalarValue,
} from "../../utils/scalar-value";
import {
  normalizePointValue,
  padColumn,
  hoverTemplate,
} from "./metric-chart-tooltip";

type TraceOptions = Pick<
  MetricChartProps,
  "metricName" | "data" | "experiments"
> & {
  display: Required<NonNullable<MetricChartProps["display"]>>;
  isFullscreen: boolean;
  hoverDisplayNames: Map<string, string>;
};

export function buildMetricChartTraces({
  metricName,
  data,
  experiments: { selectedExperiments, allExperiments },
  display: { smoothing, dotThreshold, hoverMode },
  isFullscreen,
  hoverDisplayNames,
}: TraceOptions): Partial<PlotData>[] {
  const traces: Partial<PlotData>[] = [];
  const hoverNameColumnWidth = Math.max(
    1,
    ...selectedExperiments.map(
      (experiment) =>
        (hoverDisplayNames.get(experiment.id) ?? experiment.name).length,
    ),
  );
  selectedExperiments.forEach((experiment) => {
    const originalIndex = allExperiments.findIndex(
      (item) => item.id === experiment.id,
    );
    const experimentColor =
      experiment.color || CHART_COLORS[originalIndex % CHART_COLORS.length];
    const plotPoints = data
      .map((point) => {
        const value = normalizePointValue(point[experiment.id]);
        if (!value) {
          return null;
        }
        return {
          step: point.step,
          original: value.original,
          smoothed: value.smoothed,
        };
      })
      .filter(
        (
          point,
        ): point is {
          step: number;
          original: ScalarWireValue;
          smoothed: ScalarWireValue;
        } => point !== null,
      );

    const originalSeries = buildScalarPlotSeries(
      plotPoints.map((point) => ({ step: point.step, value: point.original })),
    );
    const smoothedSeries =
      smoothing > 0
        ? buildScalarPlotSeries(
            plotPoints.map((point) => ({
              step: point.step,
              value: point.smoothed,
            })),
          )
        : originalSeries;
    const activeSeries = smoothing > 0 ? smoothedSeries : originalSeries;

    const plotPointByStep = new Map(
      plotPoints.map((point) => [point.step, point]),
    );
    const hoverLabel = hoverDisplayNames.get(experiment.id) ?? experiment.name;
    const buildCustomData = (lineX: number[], lineY: Array<number | null>) =>
      lineX.map((step, index) => {
        const point = plotPointByStep.get(step);
        const activeValue = smoothing > 0 ? point?.smoothed : point?.original;
        const displayValue =
          lineY[index] === null || activeValue === undefined
            ? "—"
            : formatScalarWireForDisplay(activeValue);
        return [
          experiment.id,
          experiment.name,
          metricName,
          point?.original ?? activeValue ?? "—",
          point?.smoothed ?? activeValue ?? "—",
          step,
          experimentColor,
          padColumn(hoverLabel, hoverNameColumnWidth),
          padColumn(String(step), 4, "left"),
          padColumn(displayValue, 8, "left"),
          hoverLabel,
        ];
      });

    const finitePointCount = plotPoints.filter((point) =>
      isFiniteScalarValue(point.original),
    ).length;
    const mode = finitePointCount <= dotThreshold ? "lines+markers" : "lines";

    if (smoothing > 0 && originalSeries.line.x.length > 0) {
      traces.push({
        x: originalSeries.line.x,
        y: originalSeries.line.y,
        customdata: buildCustomData(
          originalSeries.line.x,
          originalSeries.line.y,
        ),
        type: "scatter",
        mode,
        name: `${experiment.name} original`,
        opacity: 0.24,
        connectgaps: false,
        line: {
          color: experimentColor,
          width: isFullscreen ? 1.5 : 1,
        },
        marker: {
          color: experimentColor,
          size: isFullscreen ? 5 : 4,
        },
        hoverinfo: "skip",
      });
    }

    if (activeSeries.line.x.length > 0) {
      traces.push({
        x: activeSeries.line.x,
        y: activeSeries.line.y,
        customdata: buildCustomData(activeSeries.line.x, activeSeries.line.y),
        type: "scatter",
        mode,
        name: experiment.name,
        connectgaps: false,
        line: {
          color: experimentColor,
          width: isFullscreen ? 2 : 1.5,
        },
        marker: {
          color: experimentColor,
          size: isFullscreen ? 5 : 4,
        },
        hoverinfo: usesUnifiedMultiHover(hoverMode) ? "none" : undefined,
        hovertemplate: usesUnifiedMultiHover(hoverMode)
          ? undefined
          : hoverTemplate(hoverMode),
      });
    }

    if (activeSeries.markers.length > 0) {
      traces.push({
        x: activeSeries.markers.map((marker) => marker.step),
        y: activeSeries.markers.map((marker) => marker.y),
        type: "scatter",
        mode: "markers",
        name: `${experiment.name} non-finite`,
        showlegend: false,
        marker: {
          color: experimentColor,
          size: isFullscreen ? 9 : 7,
          symbol: activeSeries.markers.map((marker) =>
            markerSymbolForScalarMarker(marker),
          ),
        },
        hoverinfo: "skip",
      });
    }
  });
  return traces;
}
