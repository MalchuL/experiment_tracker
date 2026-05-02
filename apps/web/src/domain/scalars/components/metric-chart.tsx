"use client";

import { memo, useCallback, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import Plot from "react-plotly.js";
import type { Config, Layout, PlotData, PlotMouseEvent } from "plotly.js";

type RelayoutEvent = Readonly<Record<string, unknown>>;
type AxisWithUnifiedHoverTitle = NonNullable<Partial<Layout>["xaxis"]> & {
  unifiedhovertitle?: {
    text: string;
  };
};
interface MultiHoverRow {
  experimentName: string;
  step: number;
  value: number;
  color: string;
  displayName: string;
  displayStep: string;
  displayValue: string;
}

interface ValueColumnWidths {
  integer: number;
  fraction: number;
  suffix: number;
  hasDecimal: boolean;
}

interface MultiHoverState {
  x: number;
  y: number;
  graphWidth: number;
  graphHeight: number;
  rows: MultiHoverRow[];
}

// Tooltip geometry is estimated because the custom hover is positioned before layout measurement.
const TOOLTIP_EDGE_OFFSET_PX = 4;
const TOOLTIP_CURSOR_OFFSET_PX = 4;
const TOOLTIP_MIN_WIDTH_PX = 120;
const TOOLTIP_MIN_HEIGHT_PX = 80;
const TOOLTIP_MAX_WIDTH_PX = 520;
const TOOLTIP_MAX_HEIGHT_PX = 480;
const TOOLTIP_MONOSPACE_CHAR_WIDTH_PX = 7;
const TOOLTIP_HORIZONTAL_PADDING_PX = 24;
const TOOLTIP_ROW_HEIGHT_PX = 18;
const TOOLTIP_VERTICAL_PADDING_PX = 12;
const TOOLTIP_EXTRA_TEXT_CHARS = 8;
const PLOT_STYLE = { width: "100%", height: "100%" };

interface StablePlotProps {
  data: Partial<PlotData>[];
  layout: Partial<Layout>;
  config: Partial<Config>;
  revision?: number;
  onHover: (event: Readonly<PlotMouseEvent>) => void;
  onUnhover?: () => void;
  onRelayout: (event: RelayoutEvent) => void;
}

function StablePlot({ data, layout, config, revision, onHover, onUnhover, onRelayout }: StablePlotProps) {
  return (
    <Plot
      data={data}
      layout={layout}
      config={config}
      revision={revision}
      style={PLOT_STYLE}
      useResizeHandler={true}
      onHover={onHover}
      onUnhover={onUnhover}
      onRelayout={onRelayout}
    />
  );
}

const MemoizedPlot = memo(StablePlot);

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
  resizeRevision?: number;
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
  resizeRevision,
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
  const [multiHover, setMultiHover] = useState<MultiHoverState | null>(null);

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
        hoverinfo: hoverMode === "compare" ? "none" : undefined,
        hovertemplate: hoverMode === "compare" ? undefined : hoverTemplate(hoverMode),
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
    if (hoverMode === "compare") {
      setMultiHover(buildMultiHoverState(event, hoverNameMaxLength));
    }
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
  }, [hoverMode, hoverNameMaxLength]);

  const handleUnhover = useCallback(() => {
    activePointRef.current = null;
    setMultiHover(null);
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

  const handleResetAxes = useCallback(() => {
    onDomainChange?.({ x: null, y: null });
  }, [onDomainChange]);

  const layout = useMemo<Partial<Layout>>(() => {
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

    return {
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
  }, [domain?.x, domain?.y, dragMode, height, hoverMode, isFullscreen]);

  const config = useMemo<Partial<Config>>(() => {
    const modeBarButtonsToAdd = [
      {
        name: "Reset axes",
        title: "Reset axes",
        icon: RESET_AXES_ICON,
        click: handleResetAxes,
      },
    ];
    if (onHoverModeChange) {
      modeBarButtonsToAdd.push({
        name: hoverMode === "compare" ? "Hover nearest" : "Hover all",
        title:
          hoverMode === "compare"
            ? "Show only nearest experiment on hover"
            : "Show all experiments on hover",
        icon: hoverMode === "compare" ? HOVER_ALL_ICON : HOVER_NEAREST_ICON,
        click: () => onHoverModeChange(hoverMode === "compare" ? "nearest" : "compare"),
      });
    }
    return {
      displayModeBar: true,
      modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "resetScale2d"],
      modeBarButtonsToAdd,
      displaylogo: false,
      responsive: true,
    };
  }, [handleResetAxes, hoverMode, onHoverModeChange]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data for selected experiments
      </div>
    );
  }

  return (
    <div
      className="relative"
      style={{ height }}
      onContextMenu={handleContextMenu}
      onPointerLeave={handleUnhover}
    >
      <MemoizedPlot
        data={plotData}
        layout={layout}
        config={config}
        revision={resizeRevision}
        onHover={handleHover}
        onUnhover={hoverMode === "compare" ? undefined : handleUnhover}
        onRelayout={handleRelayout}
      />
      {hoverMode === "compare" && multiHover ? <MultiHoverTooltip hover={multiHover} /> : null}
    </div>
  );
}

function MultiHoverTooltip({ hover }: { hover: MultiHoverState }) {
  const estimatedWidth = estimateTooltipWidth(hover.rows);
  const estimatedHeight = estimateTooltipHeight(hover.rows);
  const left =
    hover.x + estimatedWidth + TOOLTIP_CURSOR_OFFSET_PX > hover.graphWidth
      ? Math.max(TOOLTIP_EDGE_OFFSET_PX, hover.x - estimatedWidth - TOOLTIP_CURSOR_OFFSET_PX)
      : hover.x + TOOLTIP_CURSOR_OFFSET_PX;
  const top =
    hover.y + estimatedHeight + TOOLTIP_CURSOR_OFFSET_PX > hover.graphHeight
      ? Math.max(TOOLTIP_EDGE_OFFSET_PX, hover.y - estimatedHeight - TOOLTIP_CURSOR_OFFSET_PX)
      : Math.max(TOOLTIP_EDGE_OFFSET_PX, hover.y - TOOLTIP_CURSOR_OFFSET_PX);
  return (
    <div
      className="pointer-events-none absolute z-20 rounded border border-white/70 bg-white/90 px-2 py-1 font-mono text-[11px] text-slate-950 shadow"
      style={{
        left,
        top,
        maxWidth: Math.max(TOOLTIP_MIN_WIDTH_PX, hover.graphWidth - TOOLTIP_EDGE_OFFSET_PX * 2),
        maxHeight: Math.max(TOOLTIP_MIN_HEIGHT_PX, hover.graphHeight - TOOLTIP_EDGE_OFFSET_PX * 2),
        overflow: "hidden",
      }}
    >
      <div className="space-y-0.5">
        {hover.rows.map((row) => (
          <div
            key={`${row.experimentName}:${row.step}`}
            className="whitespace-pre"
          >
            <span style={{ color: row.color }}>━━━━</span>
            {" "}
            {row.displayName} {row.displayStep} {row.displayValue}
          </div>
        ))}
      </div>
    </div>
  );
}

function buildMultiHoverState(
  event: Readonly<PlotMouseEvent>,
  hoverNameMaxLength: number
): MultiHoverState | null {
  const mouseEvent = event.event as unknown as globalThis.MouseEvent | undefined;
  const graphElement = findPlotlyGraphElement(mouseEvent?.target ?? null);
  if (!mouseEvent || !graphElement) {
    return null;
  }
  const rect = graphElement.getBoundingClientRect();
  const rows = (event.points ?? [])
    .map((point): MultiHoverRow | null => {
      const trace = point.data as { hoverinfo?: string } | undefined;
      const customData = point.customdata;
      if (trace?.hoverinfo === "skip" || !Array.isArray(customData) || customData.length < 7) {
        return null;
      }
      const [, experimentName, , originalValue, smoothedValue, step, color] = customData;
      const displayedValue = typeof point.y === "number" ? point.y : Number(point.y);
      if (
        typeof experimentName !== "string" ||
        typeof color !== "string" ||
        typeof step !== "number" ||
        typeof originalValue !== "number" ||
        typeof smoothedValue !== "number" ||
        !Number.isFinite(displayedValue)
      ) {
        return null;
      }
      return {
        experimentName,
        step,
        value: displayedValue,
        color,
        displayName: padColumn(truncateName(experimentName, hoverNameMaxLength), hoverNameMaxLength),
        displayStep: padColumn(String(step), 4, "left"),
        displayValue: padColumn(formatScalarValue(displayedValue), 8, "left"),
      };
    })
    .filter((row): row is MultiHoverRow => row !== null)
    .sort((a, b) => b.value - a.value);
  if (!rows.length) {
    return null;
  }
  const nameWidth = Math.max(1, ...rows.map((row) => truncateName(row.experimentName, hoverNameMaxLength).length));
  const valueColumnWidths = getValueColumnWidths(rows);
  const formattedRows = rows.map((row) => ({
    ...row,
    displayName: padColumn(truncateName(row.experimentName, hoverNameMaxLength), nameWidth),
    displayValue: formatScalarValueForColumn(row.value, valueColumnWidths),
  }));
  return {
    x: mouseEvent.clientX - rect.left,
    y: mouseEvent.clientY - rect.top,
    graphWidth: rect.width,
    graphHeight: rect.height,
    rows: formattedRows,
  };
}

function estimateTooltipWidth(rows: MultiHoverRow[]): number {
  const maxChars = Math.max(
    1,
    ...rows.map((row) => row.displayName.length + row.displayStep.length + row.displayValue.length + TOOLTIP_EXTRA_TEXT_CHARS)
  );
  return Math.min(
    TOOLTIP_MAX_WIDTH_PX,
    maxChars * TOOLTIP_MONOSPACE_CHAR_WIDTH_PX + TOOLTIP_HORIZONTAL_PADDING_PX
  );
}

function estimateTooltipHeight(rows: MultiHoverRow[]): number {
  return Math.min(
    TOOLTIP_MAX_HEIGHT_PX,
    rows.length * TOOLTIP_ROW_HEIGHT_PX + TOOLTIP_VERTICAL_PADDING_PX
  );
}

function pickNearestHoverPoint(event: Readonly<PlotMouseEvent>) {
  const points = event.points ?? [];
  if (points.length <= 1) {
    return points[0];
  }
  const mouseEvent = event.event as unknown as globalThis.MouseEvent | undefined;
  if (!mouseEvent || typeof mouseEvent.clientY !== "number") {
    return points[0];
  }
  const clientY = mouseEvent.clientY;
  const graphElement = findPlotlyGraphElement(mouseEvent.target);
  const plotLocalY = graphElement ? clientY - graphElement.getBoundingClientRect().top : clientY;
  let bestPoint = points[0];
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const point of points) {
    const yaxis = point.yaxis as { l2p?: (value: number) => number; _offset?: number } | undefined;
    const y = typeof point.y === "number" ? point.y : Number(point.y);
    if (!yaxis?.l2p || !Number.isFinite(y)) {
      continue;
    }
    const pointLocalY = (yaxis._offset ?? 0) + yaxis.l2p(y);
    const distance = Math.abs(pointLocalY - plotLocalY);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestPoint = point;
    }
  }
  return bestPoint;
}

function findPlotlyGraphElement(target: EventTarget | null): Element | null {
  if (!(target instanceof Element)) {
    return null;
  }
  return target.closest(".js-plotly-plot");
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

function getValueColumnWidths(rows: MultiHoverRow[]): ValueColumnWidths {
  const parts = rows.map((row) => splitScalarValue(formatScalarValue(row.value)));
  return {
    integer: Math.max(1, ...parts.map((part) => part.integer.length)),
    fraction: Math.max(0, ...parts.map((part) => part.fraction.length)),
    suffix: Math.max(0, ...parts.map((part) => part.suffix.length)),
    hasDecimal: parts.some((part) => part.fraction.length > 0),
  };
}

function formatScalarValueForColumn(value: number, widths: ValueColumnWidths): string {
  const part = splitScalarValue(formatScalarValue(value));
  const integer = padColumn(part.integer, widths.integer, "left");
  const decimal = widths.hasDecimal ? "." : "";
  const fraction = widths.hasDecimal ? padColumn(part.fraction, widths.fraction) : "";
  const suffix = padColumn(part.suffix, widths.suffix);
  return `${integer}${decimal}${fraction}${suffix}`;
}

function splitScalarValue(value: string) {
  const exponentIndex = value.search(/[eE]/);
  const suffix = exponentIndex === -1 ? "" : value.slice(exponentIndex);
  const mantissa = exponentIndex === -1 ? value : value.slice(0, exponentIndex);
  const decimalIndex = mantissa.indexOf(".");
  if (decimalIndex === -1) {
    return {
      integer: mantissa,
      fraction: "",
      suffix,
    };
  }
  return {
    integer: mantissa.slice(0, decimalIndex),
    fraction: mantissa.slice(decimalIndex + 1),
    suffix,
  };
}

const HOVER_NEAREST_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 450H880V550H120V450Z",
};

const RESET_AXES_ICON = {
  width: 1000,
  height: 1000,
  path: "M500 120C320 120 170 250 135 420H35L185 600L335 420H235C268 305 374 220 500 220C655 220 780 345 780 500C780 655 655 780 500 780C410 780 330 738 279 672L199 732C268 823 377 880 500 880C710 880 880 710 880 500C880 290 710 120 500 120Z",
};

const HOVER_ALL_ICON = {
  width: 1000,
  height: 1000,
  path: "M120 220H880V320H120V220ZM120 450H880V550H120V450ZM120 680H880V780H120V680Z",
};
