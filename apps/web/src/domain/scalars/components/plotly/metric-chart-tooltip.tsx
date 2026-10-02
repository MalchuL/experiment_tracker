import type { PlotMouseEvent } from "plotly.js";
import type {
  ScalarWireValue,
  ScalarPointValue,
  ScalarHoverMode,
} from "../../types";
import {
  dedupeHoverRowsByExperimentAndStep,
  filterHoverRowsToVisibleYRange,
  resolveHoverYRangeFromEvent,
} from "../../utils/metric-chart-hover";
import { formatScalarWireForDisplay } from "../../utils/scalar-value";

interface MultiHoverRow {
  experimentId: string;
  hoverLabel: string;
  step: number;
  /** Raw logged value shown in the tooltip */
  value: ScalarWireValue;
  /** Smoothed value used only for ordering rows when smoothing is on */
  sortValue: number;
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

export interface MultiHoverState {
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
export function MultiHoverTooltip({ hover }: { hover: MultiHoverState }) {
  const estimatedWidth = estimateTooltipWidth(hover.rows);
  const estimatedHeight = estimateTooltipHeight(hover.rows);
  const left =
    hover.x + estimatedWidth + TOOLTIP_CURSOR_OFFSET_PX > hover.graphWidth
      ? Math.max(
          TOOLTIP_EDGE_OFFSET_PX,
          hover.x - estimatedWidth - TOOLTIP_CURSOR_OFFSET_PX,
        )
      : hover.x + TOOLTIP_CURSOR_OFFSET_PX;
  const top =
    hover.y + estimatedHeight + TOOLTIP_CURSOR_OFFSET_PX > hover.graphHeight
      ? Math.max(
          TOOLTIP_EDGE_OFFSET_PX,
          hover.y - estimatedHeight - TOOLTIP_CURSOR_OFFSET_PX,
        )
      : Math.max(TOOLTIP_EDGE_OFFSET_PX, hover.y - TOOLTIP_CURSOR_OFFSET_PX);
  return (
    <div
      className="pointer-events-none absolute z-20 rounded border border-border bg-popover px-2 py-1 font-mono text-[11px] text-popover-foreground shadow-md"
      style={{
        left,
        top,
        maxWidth: Math.max(
          TOOLTIP_MIN_WIDTH_PX,
          hover.graphWidth - TOOLTIP_EDGE_OFFSET_PX * 2,
        ),
        maxHeight: Math.max(
          TOOLTIP_MIN_HEIGHT_PX,
          hover.graphHeight - TOOLTIP_EDGE_OFFSET_PX * 2,
        ),
        overflow: "hidden",
      }}
    >
      <div className="space-y-0.5">
        {hover.rows.map((row) => (
          <div
            key={`${row.experimentId}:${row.step}`}
            className="whitespace-pre"
          >
            <span style={{ color: row.color }}>━━━━</span> {row.displayName}{" "}
            {row.displayStep} {row.displayValue}
          </div>
        ))}
      </div>
    </div>
  );
}

export function buildMultiHoverState(
  event: Readonly<PlotMouseEvent>,
  hoverDisplayNames: Map<string, string>,
  options: {
    filterToVisibleYRange: boolean;
    domainY: [number, number] | null;
  },
): MultiHoverState | null {
  const mouseEvent = event.event as unknown as
    globalThis.MouseEvent | undefined;
  const graphElement = findPlotlyGraphElement(mouseEvent?.target ?? null);
  if (!mouseEvent || !graphElement) {
    return null;
  }
  const rect = graphElement.getBoundingClientRect();
  let rows = dedupeHoverRowsByExperimentAndStep(
    (event.points ?? [])
      .map((point): MultiHoverRow | null => {
        const trace = point.data as { hoverinfo?: string } | undefined;
        const customData = point.customdata;
        if (
          trace?.hoverinfo === "skip" ||
          !Array.isArray(customData) ||
          customData.length < 7
        ) {
          return null;
        }
        const [
          experimentId,
          experimentName,
          ,
          originalValue,
          smoothedValue,
          step,
          color,
        ] = customData;
        const sortValue =
          typeof point.y === "number" ? point.y : Number(point.y);
        if (
          typeof experimentId !== "string" ||
          typeof experimentName !== "string" ||
          typeof color !== "string" ||
          typeof step !== "number" ||
          !isScalarWireValue(originalValue) ||
          !isScalarWireValue(smoothedValue) ||
          !Number.isFinite(sortValue)
        ) {
          return null;
        }
        const hoverLabel =
          hoverDisplayNames.get(experimentId) ?? experimentName;
        const displayValue = originalValue;
        return {
          experimentId,
          hoverLabel,
          step,
          value: displayValue,
          sortValue,
          color,
          displayName: hoverLabel,
          displayStep: padColumn(String(step), 4, "left"),
          displayValue: padColumn(
            formatScalarWireForDisplay(displayValue),
            8,
            "left",
          ),
        };
      })
      .filter((row): row is MultiHoverRow => row !== null),
  ).sort((a, b) => b.sortValue - a.sortValue);
  if (options.filterToVisibleYRange) {
    const yRange = resolveHoverYRangeFromEvent(event.points, options.domainY);
    rows = filterHoverRowsToVisibleYRange(rows, yRange);
  }
  if (!rows.length) {
    return null;
  }
  const nameWidth = Math.max(1, ...rows.map((row) => row.hoverLabel.length));
  const valueColumnWidths = getValueColumnWidths(rows);
  const formattedRows = rows.map((row) => ({
    ...row,
    displayName: padColumn(row.hoverLabel, nameWidth),
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
    ...rows.map(
      (row) =>
        row.displayName.length +
        row.displayStep.length +
        row.displayValue.length +
        TOOLTIP_EXTRA_TEXT_CHARS,
    ),
  );
  return Math.min(
    TOOLTIP_MAX_WIDTH_PX,
    maxChars * TOOLTIP_MONOSPACE_CHAR_WIDTH_PX + TOOLTIP_HORIZONTAL_PADDING_PX,
  );
}

function estimateTooltipHeight(rows: MultiHoverRow[]): number {
  return Math.min(
    TOOLTIP_MAX_HEIGHT_PX,
    rows.length * TOOLTIP_ROW_HEIGHT_PX + TOOLTIP_VERTICAL_PADDING_PX,
  );
}

export function pickNearestHoverPoint(event: Readonly<PlotMouseEvent>) {
  const points = event.points ?? [];
  if (points.length <= 1) {
    return points[0];
  }
  const mouseEvent = event.event as unknown as
    globalThis.MouseEvent | undefined;
  if (!mouseEvent || typeof mouseEvent.clientY !== "number") {
    return points[0];
  }
  const clientY = mouseEvent.clientY;
  const graphElement = findPlotlyGraphElement(mouseEvent.target);
  const plotLocalY = graphElement
    ? clientY - graphElement.getBoundingClientRect().top
    : clientY;
  let bestPoint = points[0];
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const point of points) {
    const yaxis = point.yaxis as
      { l2p?: (value: number) => number; _offset?: number } | undefined;
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

export function isScalarWireValue(value: unknown): value is ScalarWireValue {
  return (
    typeof value === "number" ||
    value === "nan" ||
    value === "inf" ||
    value === "-inf"
  );
}

export function normalizePointValue(
  value: ScalarWireValue | ScalarPointValue | null | undefined,
): ScalarPointValue | null {
  if (isScalarWireValue(value)) {
    return { original: value, smoothed: value };
  }
  if (
    !value ||
    !isScalarWireValue(value.original) ||
    !isScalarWireValue(value.smoothed)
  ) {
    return null;
  }
  return value;
}

export function hoverTemplate(hoverMode: ScalarHoverMode): string {
  if (hoverMode === "nearest") {
    return (
      "<span style='color:%{customdata[6]};font-weight:700'>━━━━</span> " +
      "%{customdata[10]} %{customdata[5]} %{customdata[9]}<extra></extra>"
    );
  }
  return "%{customdata[7]} %{customdata[8]} %{customdata[9]}<extra></extra>";
}

export function padColumn(
  value: string,
  width: number,
  align: "left" | "right" = "right",
): string {
  const gap = Math.max(0, width - value.length);
  const padding = "\u00A0".repeat(gap);
  return align === "left" ? `${padding}${value}` : `${value}${padding}`;
}

function formatScalarValue(value: ScalarWireValue): string {
  return formatScalarWireForDisplay(value);
}

function getValueColumnWidths(rows: MultiHoverRow[]): ValueColumnWidths {
  const parts = rows.map((row) =>
    splitScalarValue(formatScalarValue(row.value)),
  );
  return {
    integer: Math.max(1, ...parts.map((part) => part.integer.length)),
    fraction: Math.max(0, ...parts.map((part) => part.fraction.length)),
    suffix: Math.max(0, ...parts.map((part) => part.suffix.length)),
    hasDecimal: parts.some((part) => part.fraction.length > 0),
  };
}

function formatScalarValueForColumn(
  value: ScalarWireValue,
  widths: ValueColumnWidths,
): string {
  const part = splitScalarValue(formatScalarValue(value));
  const integer = padColumn(part.integer, widths.integer, "left");
  const decimal = widths.hasDecimal ? "." : "";
  const fraction = widths.hasDecimal
    ? padColumn(part.fraction, widths.fraction)
    : "";
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
