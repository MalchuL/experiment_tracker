"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import ColorPicker from "@/components/ui/color-picker";
import { ChevronLeft, ChevronRight, Palette, Trash2, X } from "lucide-react";
import { cn, createClientId } from "@/lib/utils";
import { useSelectiveProjectMetrics } from "@/domain/experiments/hooks";
import type { Experiment } from "@/domain/experiments/types";
import { MetricDirection } from "@/domain/metrics/types";
import { formatMetricLabel, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import { CHART_COLORS } from "@/domain/scalars/constants";
import { ScalarCardResizeHandle } from "@/domain/scalars/components/charts/scalar-card-resize-handle";
import { buildMetricsPlotData } from "../lib/build-metrics-plot-data";
import {
  applyYRangeToChartData,
  collectPlotNumericValues,
  computeComparePlotChartLayout,
  computeUniformYTicks,
  lineChartBottomMargin,
  parseYBoundInput,
  resolveComparePlotYDomain,
  resolveYDomainFromDrafts,
  xAxisTickTextAnchor,
} from "../lib/compute-plot-chart-layout";
import type { ComparePlotConfig, MetricNameOption, PlotMetricSeries } from "../types/metrics-compare";
import {
  DEFAULT_COMPARE_PLOT_HEIGHT,
  DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE,
  DEFAULT_COMPARE_PLOT_POINT_PADDING,
  MAX_COMPARE_PLOT_HEIGHT,
  MAX_COMPARE_PLOT_NAME_LABEL_FONT_SIZE,
  MAX_COMPARE_PLOT_POINT_PADDING,
  MIN_COMPARE_PLOT_HEIGHT,
  MIN_COMPARE_PLOT_NAME_LABEL_FONT_SIZE,
} from "../types/metrics-compare";
import { MetricsCompareMetricPicker } from "./metrics-compare-metric-picker";
import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";

const CHART_CLASS =
  "!aspect-auto h-full w-full min-h-0 [&_.recharts-cartesian-grid_line]:stroke-border/40 [&_.recharts-reference-line_line]:stroke-border/45";

type MetricsComparePlotCardProps = {
  projectId: string;
  plot: ComparePlotConfig;
  selectedExperiments: Experiment[];
  metricOptions: MetricNameOption[];
  onPatchPlot: (plotId: string, patch: Partial<ComparePlotConfig>) => void;
  onRemove: () => void;
};

export function MetricsComparePlotCard({
  projectId,
  plot,
  selectedExperiments,
  metricOptions,
  onPatchPlot,
  onRemove,
}: MetricsComparePlotCardProps) {
  const [settingsOpen, setSettingsOpen] = useState(true);
  const [yMinDraft, setYMinDraft] = useState(() => formatYBound(plot.yMin));
  const [yMaxDraft, setYMaxDraft] = useState(() => formatYBound(plot.yMax));
  const [yBoundLastEdited, setYBoundLastEdited] = useState<"min" | "max" | null>(null);

  const pointPadding = plot.pointPadding ?? DEFAULT_COMPARE_PLOT_POINT_PADDING;
  const plotHeight = plot.plotHeight ?? DEFAULT_COMPARE_PLOT_HEIGHT;
  const nameLabelFontSize = plot.nameLabelFontSize ?? DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE;
  const seriesIds = useMemo(() => plot.series.map((series) => series.id), [plot.series]);

  const projectMetrics = useMemo(
    () =>
      plot.series.map((series) => ({
        name: series.name,
        label: series.label,
        direction: MetricDirection.MAXIMIZE,
        aggregation: "last" as const,
      })),
    [plot.series]
  );

  const { metricsByExperiment, isLoading } = useSelectiveProjectMetrics(
    projectId,
    selectedExperiments.map((experiment) => experiment.id),
    projectMetrics
  );

  const chartData = useMemo(
    () => buildMetricsPlotData(selectedExperiments, metricsByExperiment, plot.series),
    [selectedExperiments, metricsByExperiment, plot.series]
  );

  const numericValues = useMemo(
    () => collectPlotNumericValues(chartData, seriesIds),
    [chartData, seriesIds]
  );

  const yDomainResult = useMemo(
    () =>
      resolveYDomainFromDrafts({
        yMinDraft,
        yMaxDraft,
        yMin: plot.yMin,
        yMax: plot.yMax,
        values: numericValues,
        lastEdited: yBoundLastEdited,
      }),
    [yMinDraft, yMaxDraft, plot.yMin, plot.yMax, numericValues, yBoundLastEdited]
  );

  const chartDataFiltered = useMemo(
    () => applyYRangeToChartData(chartData, seriesIds, yDomainResult.domain),
    [chartData, seriesIds, yDomainResult.domain]
  );

  const yAxisTicks = useMemo(
    () => computeUniformYTicks(yDomainResult.domain),
    [yDomainResult.domain]
  );
  const referenceLinePoints = useMemo(
    () =>
      chartData.filter(
        (point) =>
          typeof point.experimentId === "string" &&
          point.experimentId.trim().length > 0
      ),
    [chartData]
  );

  const experimentNameById = useMemo(() => {
    const names = new Map<string, string>();
    for (const point of chartData) {
      names.set(point.experimentId, point.experimentName);
    }
    return names;
  }, [chartData]);

  const chartLayout = useMemo(
    () =>
      computeComparePlotChartLayout(
        selectedExperiments.map((experiment) => experiment.name),
        chartData,
        seriesIds,
        plot.nameLabelAngle,
        pointPadding,
        plotHeight,
        nameLabelFontSize
      ),
    [
      selectedExperiments,
      chartData,
      seriesIds,
      plot.nameLabelAngle,
      pointPadding,
      plotHeight,
      nameLabelFontSize,
    ]
  );

  const chartConfig = useMemo(() => {
    const config: ChartConfig = {};
    for (const series of plot.series) {
      config[series.id] = {
        label: formatMetricLabel(series.name, series.label),
        color: series.color,
      };
    }
    return config;
  }, [plot.series]);

  const excludedKeys = useMemo(
    () => new Set(plot.series.map((series) => projectMetricKeyString(series))),
    [plot.series]
  );

  const handleAddMetric = (option: MetricNameOption) => {
    if (excludedKeys.has(projectMetricKeyString(option))) {
      return;
    }
    onPatchPlot(plot.id, {
      series: [
        ...plot.series,
        {
          id: createClientId(),
          name: option.name,
          label: option.label,
          color: CHART_COLORS[plot.series.length % CHART_COLORS.length]!,
        },
      ],
    });
  };

  const handleRemoveSeries = (seriesId: string) => {
    onPatchPlot(plot.id, {
      series: plot.series.filter((series) => series.id !== seriesId),
    });
  };

  const handleColorChange = (seriesId: string, color: string) => {
    onPatchPlot(plot.id, {
      series: plot.series.map((series) =>
        series.id === seriesId ? { ...series, color } : series
      ),
    });
  };

  const handleYBoundChange = (bound: "min" | "max", draft: string) => {
    if (bound === "min") {
      setYMinDraft(draft);
    } else {
      setYMaxDraft(draft);
    }
    setYBoundLastEdited(bound);

    const parsed = parseYBoundInput(draft);
    if (parsed === undefined) {
      return;
    }

    const resolved = resolveComparePlotYDomain({
      yMin: bound === "min" ? parsed : plot.yMin ?? null,
      yMax: bound === "max" ? parsed : plot.yMax ?? null,
      values: numericValues,
      lastEdited: bound,
    });

    onPatchPlot(plot.id, {
      yMin: resolved.yMin,
      yMax: resolved.yMax,
    });
  };

  const chartHeightPx = chartLayout.chartHeight;

  return (
    <Card className="relative min-w-0 overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-end space-y-0 p-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={onRemove}
          aria-label="Remove plot"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex flex-col gap-2 p-0 pb-1 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          {plot.series.length > 0 ? (
            <PlotMetricLegend series={plot.series} fontSize={nameLabelFontSize} />
          ) : null}
          <div className="pt-2">
            {plot.series.length === 0 ? (
              <PlotPlaceholder height={chartHeightPx}>
                Add metrics from the panel on the right.
              </PlotPlaceholder>
            ) : isLoading ? (
              <PlotPlaceholder height={chartHeightPx}>Loading plot…</PlotPlaceholder>
            ) : (
              <div className="w-full shrink-0" style={{ height: chartHeightPx }}>
                <ChartContainer config={chartConfig} className={CHART_CLASS}>
                  <LineChart
                    data={chartDataFiltered}
                    margin={{
                      left: chartLayout.chartMarginHorizontal.left,
                      right: chartLayout.chartMarginHorizontal.right,
                      top: 0,
                      bottom: lineChartBottomMargin(chartLayout.xAxisHeight),
                    }}
                  >
                    <CartesianGrid horizontal vertical={false} stroke="#ccc" />
                    {referenceLinePoints.map((point) => (
                      <ReferenceLine
                        key={point.experimentId}
                        x={point.experimentId}
                        stroke="#ccc"
                        strokeOpacity={0.55}
                        ifOverflow="extendDomain"
                      />
                    ))}
                    <XAxis
                      dataKey="experimentId"
                      tickLine={false}
                      axisLine={false}
                      tickMargin={0}
                      interval={0}
                      angle={plot.nameLabelAngle}
                      textAnchor={xAxisTickTextAnchor(plot.nameLabelAngle)}
                      height={chartLayout.xAxisHeight}
                      padding={chartLayout.xAxisPadding}
                      tick={{ fontSize: nameLabelFontSize }}
                      tickFormatter={(experimentId) =>
                        experimentNameById.get(String(experimentId)) ?? String(experimentId)
                      }
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      tickMargin={0}
                      width={chartLayout.yAxisWidth}
                      domain={yDomainResult.domain}
                      allowDataOverflow
                      ticks={yAxisTicks}
                      tick={{ fontSize: nameLabelFontSize }}
                      tickFormatter={(value) => formatMetricScalarForDisplay(Number(value))}
                    />
                    <ChartTooltip
                      shared
                      cursor={{ stroke: "#ccc", strokeOpacity: 0.45, strokeWidth: 1 }}
                      content={<ComparePlotTooltipContent chartConfig={chartConfig} />}
                    />
                    {plot.series.map((series) => (
                      <Line
                        key={series.id}
                        type="monotone"
                        dataKey={series.id}
                        stroke={series.color}
                        strokeWidth={2}
                        dot={{ r: 4, fill: series.color, strokeWidth: 0 }}
                        connectNulls={false}
                      />
                    ))}
                  </LineChart>
                </ChartContainer>
              </div>
            )}
          </div>
        </div>

        <PlotSettingsPanel
          plot={plot}
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          metricOptions={metricOptions}
          excludedKeys={excludedKeys}
          yMinDraft={yMinDraft}
          yMaxDraft={yMaxDraft}
          plotHeight={plotHeight}
          pointPadding={pointPadding}
          onAddMetric={handleAddMetric}
          onRemoveSeries={handleRemoveSeries}
          onColorChange={handleColorChange}
          onYBoundChange={handleYBoundChange}
          onPatchPlot={onPatchPlot}
        />
      </CardContent>
      <ScalarCardResizeHandle
        width={720}
        height={plotHeight}
        onResize={(size) =>
          onPatchPlot(plot.id, {
            plotHeight: size.height,
          })
        }
      />
    </Card>
  );
}

function PlotMetricLegend({
  series,
  fontSize,
}: {
  series: PlotMetricSeries[];
  fontSize: number;
}) {
  const dotSizePx = (fontSize * 10) / DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE;

  return (
    <div className="flex w-full flex-wrap items-center justify-center gap-x-4 gap-y-1 px-3 pb-1">
      {series.map((item) => (
        <span
          key={item.id}
          className="inline-flex max-w-full items-center gap-1.5"
          style={{ fontSize }}
        >
          <span
            className="shrink-0 rounded-full"
            style={{
              backgroundColor: item.color,
              width: dotSizePx,
              height: dotSizePx,
            }}
          />
          <span className="truncate">{item.name}</span>
        </span>
      ))}
    </div>
  );
}

function PlotPlaceholder({
  height,
  children,
}: {
  height: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground"
      style={{ height }}
    >
      {children}
    </div>
  );
}

function PlotSettingsPanel({
  plot,
  open,
  onOpenChange,
  metricOptions,
  excludedKeys,
  yMinDraft,
  yMaxDraft,
  plotHeight,
  pointPadding,
  onAddMetric,
  onRemoveSeries,
  onColorChange,
  onYBoundChange,
  onPatchPlot,
}: {
  plot: ComparePlotConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  metricOptions: MetricNameOption[];
  excludedKeys: Set<string>;
  yMinDraft: string;
  yMaxDraft: string;
  plotHeight: number;
  pointPadding: number;
  onAddMetric: (option: MetricNameOption) => void;
  onRemoveSeries: (seriesId: string) => void;
  onColorChange: (seriesId: string, color: string) => void;
  onYBoundChange: (bound: "min" | "max", draft: string) => void;
  onPatchPlot: (plotId: string, patch: Partial<ComparePlotConfig>) => void;
}) {
  return (
    <div
      className={cn(
        "relative shrink-0 transition-[width] duration-300",
        open ? "w-full sm:w-56" : "w-0"
      )}
    >
      {open ? (
        <aside className="flex flex-col gap-3 border-t px-3 pt-3 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0">
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Add metric</p>
            <MetricsCompareMetricPicker
              options={metricOptions}
              excludedKeys={excludedKeys}
              onSelect={onAddMetric}
            />
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Y range</p>
            <div className="grid grid-cols-2 gap-2">
              <YBoundField
                id={`plot-y-min-${plot.id}`}
                label="Y min"
                value={yMinDraft}
                onChange={(value) => onYBoundChange("min", value)}
              />
              <YBoundField
                id={`plot-y-max-${plot.id}`}
                label="Y max"
                value={yMaxDraft}
                onChange={(value) => onYBoundChange("max", value)}
              />
            </div>
          </div>

          <PlotSliderField
            id={`plot-height-${plot.id}`}
            label="Plot height"
            value={plotHeight}
            min={MIN_COMPARE_PLOT_HEIGHT}
            max={MAX_COMPARE_PLOT_HEIGHT}
            step={8}
            unit="px"
            onChange={(value) => onPatchPlot(plot.id, { plotHeight: value })}
          />
          <PlotSliderField
            id={`plot-name-angle-${plot.id}`}
            label="Name angle"
            value={plot.nameLabelAngle}
            min={-90}
            max={0}
            step={5}
            unit="°"
            onChange={(value) => onPatchPlot(plot.id, { nameLabelAngle: value })}
          />
          <PlotSliderField
            id={`plot-name-size-${plot.id}`}
            label="Font size"
            value={plot.nameLabelFontSize ?? DEFAULT_COMPARE_PLOT_NAME_LABEL_FONT_SIZE}
            min={MIN_COMPARE_PLOT_NAME_LABEL_FONT_SIZE}
            max={MAX_COMPARE_PLOT_NAME_LABEL_FONT_SIZE}
            step={1}
            unit="px"
            onChange={(value) => onPatchPlot(plot.id, { nameLabelFontSize: value })}
          />
          <PlotSliderField
            id={`plot-point-padding-${plot.id}`}
            label="Point spacing"
            value={pointPadding}
            min={0}
            max={MAX_COMPARE_PLOT_POINT_PADDING}
            step={4}
            unit="px"
            onChange={(value) => onPatchPlot(plot.id, { pointPadding: value })}
          />

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Series</p>
            {plot.series.length === 0 ? (
              <p className="text-xs text-muted-foreground">No metrics added yet.</p>
            ) : (
              <ul className="max-h-48 space-y-0.5 overflow-y-auto pr-1">
                {plot.series.map((series) => (
                  <li key={series.id} className="flex items-center gap-2 rounded-sm py-1 pr-0.5">
                    <PlotSeriesColorMenu
                      color={series.color}
                      onColorChange={(color) => onColorChange(series.id, color)}
                    />
                    <span
                      className="min-w-0 flex-1 truncate text-xs"
                      title={formatMetricLabel(series.name, series.label)}
                    >
                      {formatMetricLabel(series.name, series.label)}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 text-muted-foreground"
                      onClick={() => onRemoveSeries(series.id)}
                      aria-label={`Remove ${formatMetricLabel(series.name, series.label)}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      ) : null}

      <div className="absolute -left-3 top-3 z-10">
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-6 w-6 rounded-full bg-background shadow-md transition-shadow hover:shadow-lg"
          onClick={() => onOpenChange(!open)}
          aria-label={open ? "Hide plot settings" : "Show plot settings"}
        >
          {open ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </Button>
      </div>
    </div>
  );
}

function YBoundField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type="number"
        placeholder="Auto"
        className="h-8"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function PlotSliderField({
  id,
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id} className="text-xs text-muted-foreground">
          {label}
        </Label>
        <span className="text-xs tabular-nums text-muted-foreground">
          {value}
          {unit}
        </span>
      </div>
      <Slider
        id={id}
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={([nextValue]) => {
          if (nextValue === undefined) return;
          onChange(nextValue);
        }}
      />
    </div>
  );
}

function formatYBound(value: number | null | undefined): string {
  return value != null ? String(value) : "";
}

function PlotSeriesColorMenu({
  color,
  onColorChange,
}: {
  color: string;
  onColorChange: (color: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const isPresetColor = CHART_COLORS.includes(color);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="h-3.5 w-3.5 shrink-0 rounded-full border border-border/80 ring-offset-background transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
          style={{ backgroundColor: color }}
          aria-label="Choose series color"
        />
      </PopoverTrigger>
      <PopoverContent className="w-auto p-2" align="start" sideOffset={6}>
        <div className="flex flex-wrap gap-1.5">
          <ColorPicker value={color} onChange={onColorChange}>
            <button
              type="button"
              className={cn(
                "flex h-5 w-5 items-center justify-center rounded-full border-2 transition-transform hover:scale-105",
                !isPresetColor ? "border-foreground scale-110" : "border-transparent"
              )}
              style={{ backgroundColor: color }}
              aria-label="Edit custom color"
            >
              <Palette className="h-3 w-3 text-white drop-shadow-sm" />
            </button>
          </ColorPicker>
          {CHART_COLORS.map((option) => (
            <button
              key={option}
              type="button"
              className={cn(
                "h-5 w-5 rounded-full border-2 transition-transform hover:scale-105",
                isPresetColor && color === option ? "border-foreground scale-110" : "border-transparent"
              )}
              style={{ backgroundColor: option }}
              aria-label={`Use color ${option}`}
              onClick={() => {
                onColorChange(option);
                setOpen(false);
              }}
            />
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

type ComparePlotTooltipPayloadItem = {
  dataKey?: string | number;
  value?: number | string | null;
  color?: string;
  payload?: { experimentName?: string };
};

function ComparePlotTooltipContent({
  active,
  payload,
  label,
  chartConfig,
}: {
  active?: boolean;
  payload?: ComparePlotTooltipPayloadItem[];
  label?: string | number;
  chartConfig: ChartConfig;
}) {
  if (!active || !payload?.length) return null;

  const experimentName = String(
    payload[0]?.payload?.experimentName ?? label ?? ""
  );

  const rows = payload.filter(
    (item) => item.value !== null && item.value !== undefined && item.value !== ""
  );

  if (rows.length === 0) return null;

  return (
    <div className="grid min-w-[10rem] gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{experimentName}</div>
      <div className="grid gap-1.5">
        {rows.map((item) => {
          const seriesKey = String(item.dataKey ?? "");
          const metricLabel =
            (chartConfig[seriesKey]?.label as string | undefined) ?? seriesKey;
          const numericValue =
            typeof item.value === "number" ? item.value : Number(item.value);

          return (
            <div
              key={seriesKey}
              className="flex items-center justify-between gap-4 leading-none"
            >
              <span className="flex min-w-0 items-center gap-1.5">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: item.color ?? "currentColor" }}
                />
                <span className="truncate text-muted-foreground">{metricLabel}</span>
              </span>
              <span className="shrink-0 font-mono font-medium tabular-nums text-foreground">
                {formatMetricScalarForDisplay(numericValue)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
