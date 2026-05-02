"use client";

import { useCallback, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import Plot from "react-plotly.js";
import type { Config, Layout, PlotData, PlotMouseEvent } from "plotly.js";

type RelayoutEvent = Readonly<Record<string, unknown>>;
type AxisWithUnifiedHoverTitle = NonNullable<Partial<Layout>["xaxis"]> & {
  unifiedhovertitle?: {
    text: string;
  };
};

import type { Experiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
  ScalarPointValue,
} from "@/domain/scalars/types";
import { CHART_COLORS } from "@/domain/scalars/constants";

export interface MetricChartProps {
  metricName: string;
  data: ScalarChartPoint[];
  selectedExperiments: Experiment[];
  allExperiments: Experiment[];
  height?: number;
  domain?: ChartDomain | null;
  onDomainChange?: (domain: ChartDomain | null) => void;
  isFullscreen?: boolean;
  smoothing?: number;
  dotThreshold?: number;
  hoverMode?: ScalarHoverMode;
  hoverNameMaxLength?: number;
  onHoverModeChange?: (mode: ScalarHoverMode) => void;
  onPointContextMenu?: (point: ScalarPointSelection, position: { x: number; y: number }) => void;
}

export function MetricChart({
  metricName,
  data,
  selectedExperiments,
  allExperiments,
  height = 200,
  domain,
  onDomainChange,
  isFullscreen = false,
  smoothing = 0,
  dotThreshold = 10,
  hoverMode = "compare",
  hoverNameMaxLength = 50,
  onHoverModeChange,
  onPointContextMenu,
}: MetricChartProps) {
  const [dragMode, setDragMode] = useState<"zoom" | "pan">("zoom");
  const activePointRef = useRef<ScalarPointSelection | null>(null);

  const plotData = useMemo(() => {
    const traces: Partial<PlotData>[] = [];
    const hoverNameColumnWidth = Math.max(
      1,
      ...selectedExperiments.map((experiment) =>
        truncateName(experiment.name, hoverNameMaxLength).length
      )
    );
    selectedExperiments.forEach((experiment) => {
      const originalIndex = allExperiments.findIndex((item) => item.id === experiment.id);
      const experimentColor = experiment.color || CHART_COLORS[originalIndex % CHART_COLORS.length];
      const xValues: number[] = [];
      const originalValues: number[] = [];
      const smoothedValues: number[] = [];
      const customData: Array<[string, string, string, number, number, number, string, string, string, string, string]> = [];

      data.forEach((point) => {
        const step = point.step;
        const rawValue = point[experiment.id];
        const value = normalizePointValue(rawValue);
        if (value) {
          xValues.push(step);
          originalValues.push(value.original);
          smoothedValues.push(value.smoothed);
          customData.push([
            experiment.id,
            experiment.name,
            metricName,
            value.original,
            value.smoothed,
            step,
            experimentColor,
            padColumn(truncateName(experiment.name, hoverNameColumnWidth), hoverNameColumnWidth),
            padColumn(String(step), 4, "left"),
            padColumn(formatScalarValue(value.original), 8, "left"),
            truncateName(experiment.name, hoverNameMaxLength),
          ]);
        }
      });

      const mode = xValues.length <= dotThreshold ? "lines+markers" : "lines";
      if (smoothing > 0) {
        traces.push({
          x: xValues,
          y: originalValues,
          customdata: customData,
          type: "scatter",
          mode,
          name: `${experiment.name} original`,
          opacity: 0.24,
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

      traces.push({
        x: xValues,
        y: smoothing > 0 ? smoothedValues : originalValues,
        customdata: customData,
        type: "scatter",
        mode,
        name: experiment.name,
        line: {
          color: experimentColor,
          width: isFullscreen ? 2 : 1.5,
        },
        marker: {
          color: experimentColor,
          size: isFullscreen ? 5 : 4,
        },
        hovertemplate: hoverTemplate(hoverMode),
      });
    });
    return traces;
  }, [allExperiments, data, dotThreshold, hoverMode, hoverNameMaxLength, isFullscreen, metricName, selectedExperiments, smoothing]);

  const handleRelayout = useCallback(
    (event: RelayoutEvent) => {
      if (event?.dragmode === "zoom" || event?.dragmode === "pan") {
        setDragMode(event.dragmode);
      }
      const nextDomain: ChartDomain = {
        x: domain?.x ?? null,
        y: domain?.y ?? null,
      };

      if (event["xaxis.range[0]"] !== undefined && event["xaxis.range[1]"] !== undefined) {
        nextDomain.x = [
          Number(event["xaxis.range[0]"]),
          Number(event["xaxis.range[1]"]),
        ];
      } else if (event["xaxis.autorange"] === true) {
        nextDomain.x = null;
      }

      if (event["yaxis.range[0]"] !== undefined && event["yaxis.range[1]"] !== undefined) {
        nextDomain.y = [
          Number(event["yaxis.range[0]"]),
          Number(event["yaxis.range[1]"]),
        ];
      } else if (event["yaxis.autorange"] === true) {
        nextDomain.y = null;
      }

      onDomainChange?.(nextDomain);
    },
    [domain, onDomainChange]
  );

  const handleHover = useCallback((event: Readonly<PlotMouseEvent>) => {
    const point = pickNearestHoverPoint(event);
    const customData = point?.customdata;
    if (!Array.isArray(customData) || customData.length < 6) return;
    const [experimentId, experimentName, pointMetricName, originalValue, smoothedValue, step] =
      customData;
    if (
      typeof experimentId !== "string" ||
      typeof experimentName !== "string" ||
      typeof pointMetricName !== "string" ||
      typeof originalValue !== "number" ||
      typeof smoothedValue !== "number" ||
      typeof step !== "number"
    ) {
      return;
    }
    activePointRef.current = {
      experimentId,
      experimentName,
      metricName: pointMetricName,
      step,
      originalValue,
      smoothedValue,
    };
  }, []);

  const handleContextMenu = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      const activePoint = activePointRef.current;
      if (!activePoint || !onPointContextMenu) return;
      event.preventDefault();
      onPointContextMenu(activePoint, { x: event.clientX, y: event.clientY });
    },
    [onPointContextMenu]
  );

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data for selected experiments
      </div>
    );
  }

  const xAxis: AxisWithUnifiedHoverTitle = {
    title: isFullscreen ? { text: "Step", font: { size: 12 } } : undefined,
    tickfont: { size: isFullscreen ? 12 : 10 },
    gridcolor: "rgba(128, 128, 128, 0.2)",
    range: domain?.x || undefined,
    autorange: domain?.x ? false : true,
    unifiedhovertitle: {
      text: "\u00A0",
    },
  };

  const layout: Partial<Layout> = {
    autosize: true,
    height,
    margin: {
      l: isFullscreen ? 60 : 50,
      r: 20,
      t: 10,
      b: isFullscreen ? 40 : 30,
    },
    xaxis: xAxis,
    yaxis: {
      tickfont: { size: isFullscreen ? 12 : 10 },
      gridcolor: "rgba(128, 128, 128, 0.2)",
      range: domain?.y || undefined,
      autorange: domain?.y ? false : true,
    },
    showlegend: false,
    hovermode: hoverMode === "compare" ? "x unified" : "closest",
    hoverlabel: {
      align: "left",
      namelength: -1,
      bgcolor: "rgba(255, 255, 255, 0.9)",
      bordercolor: "rgba(255, 255, 255, 0.7)",
      font: {
        color: "rgba(15, 23, 42, 0.95)",
        family: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      },
    },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    dragmode: dragMode,
  };

  const config: Partial<Config> = {
    displayModeBar: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    modeBarButtonsToAdd: onHoverModeChange
      ? [
          {
            name: hoverMode === "compare" ? "Hover nearest" : "Hover all",
            title:
              hoverMode === "compare"
                ? "Show only nearest experiment on hover"
                : "Show all experiments on hover",
            icon: hoverMode === "compare" ? HOVER_ALL_ICON : HOVER_NEAREST_ICON,
            click: () => onHoverModeChange(hoverMode === "compare" ? "nearest" : "compare"),
          },
        ]
      : undefined,
    displaylogo: false,
    responsive: true,
  };

  return (
    <div style={{ height }} onContextMenu={handleContextMenu}>
      <Plot
        data={plotData}
        layout={layout}
        config={config}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler={true}
        onHover={handleHover}
        onRelayout={handleRelayout}
      />
    </div>
  );
}

function pickNearestHoverPoint(event: Readonly<PlotMouseEvent>) {
  const points = event.points ?? [];
  if (points.length <= 1) {
    return points[0];
  }
  const mouseEvent = event.event as unknown as globalThis.MouseEvent | undefined;
  const clientY = mouseEvent?.clientY;
  if (typeof clientY !== "number") {
    return points[0];
  }
  let bestPoint = points[0];
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const point of points) {
    const yaxis = point.yaxis as { l2p?: (value: number) => number; _offset?: number } | undefined;
    const y = typeof point.y === "number" ? point.y : Number(point.y);
    if (!yaxis?.l2p || !Number.isFinite(y)) {
      continue;
    }
    const pointClientY = (yaxis._offset ?? 0) + yaxis.l2p(y);
    const distance = Math.abs(pointClientY - clientY);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestPoint = point;
    }
  }
  return bestPoint;
}

function normalizePointValue(
  value: number | ScalarPointValue | null | undefined
): ScalarPointValue | null {
  if (typeof value === "number") {
    return { original: value, smoothed: value };
  }
  if (!value || typeof value.original !== "number" || typeof value.smoothed !== "number") {
    return null;
  }
  return value;
}

function hoverTemplate(hoverMode: ScalarHoverMode): string {
  if (hoverMode === "nearest") {
    return (
      "<span style='color:%{customdata[6]};font-weight:700'>━━━━</span> " +
      "%{customdata[10]} %{customdata[5]} %{customdata[3]:.6g}<extra></extra>"
    );
  }
  return "%{customdata[7]} %{customdata[8]} %{customdata[9]}<extra></extra>";
}

function truncateName(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }
  if (maxLength <= 1) {
    return value.slice(0, maxLength);
  }
  return `${value.slice(0, maxLength - 1)}…`;
}

function padColumn(value: string, width: number, align: "left" | "right" = "right"): string {
  const gap = Math.max(0, width - value.length);
  const padding = "\u00A0".repeat(gap);
  return align === "left" ? `${padding}${value}` : `${value}${padding}`;
}

function formatScalarValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toPrecision(6);
}

const HOVER_NEAREST_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 450H880V550H120V450Z",
};

const HOVER_ALL_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 220H880V320H120V220ZM120 450H880V550H120V450ZM120 680H880V780H120V680Z",
};
