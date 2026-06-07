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
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import ColorPicker from "@/components/ui/color-picker";
import { Palette, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSelectiveProjectMetrics } from "@/domain/experiments/hooks";
import type { Experiment } from "@/domain/experiments/types";
import { MetricDirection } from "@/domain/metrics/types";
import { formatMetricLabel, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import { CHART_COLORS } from "@/domain/scalars/constants";
import { buildMetricsPlotData } from "../lib/build-metrics-plot-data";
import { computeComparePlotChartLayout, lineChartBottomMargin, xAxisTickTextAnchor } from "../lib/compute-plot-chart-layout";
import type { ComparePlotConfig, MetricNameOption } from "../types/metrics-compare";
import { MAX_COMPARE_PLOT_POINT_PADDING, DEFAULT_COMPARE_PLOT_POINT_PADDING } from "../types/metrics-compare";
import { MetricsCompareMetricPicker } from "./metrics-compare-metric-picker";
import { formatMetricScalarForDisplay } from "@/lib/metrics/metric-value-display";

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
  const nameLabelAngle = plot.nameLabelAngle;
  const pointPadding = plot.pointPadding ?? DEFAULT_COMPARE_PLOT_POINT_PADDING;
  const experimentIds = selectedExperiments.map((e) => e.id);
  const projectMetrics = useMemo(
    () =>
      plot.series.map((s) => ({
        name: s.name,
        label: s.label,
        direction: MetricDirection.MAXIMIZE,
        aggregation: "last" as const,
      })),
    [plot.series]
  );

  const { metricsByExperiment, isLoading } = useSelectiveProjectMetrics(
    projectId,
    experimentIds,
    projectMetrics
  );

  const chartData = useMemo(
    () => buildMetricsPlotData(selectedExperiments, metricsByExperiment, plot.series),
    [selectedExperiments, metricsByExperiment, plot.series]
  );

  const chartLayout = useMemo(
    () =>
      computeComparePlotChartLayout(
        selectedExperiments.map((experiment) => experiment.name),
        chartData,
        plot.series.map((s) => s.id),
        nameLabelAngle,
        pointPadding
      ),
    [selectedExperiments, chartData, plot.series, nameLabelAngle, pointPadding]
  );

  const chartConfig = useMemo(() => {
    const config: ChartConfig = {};
    for (const s of plot.series) {
      config[s.id] = {
        label: formatMetricLabel(s.name, s.label),
        color: s.color,
      };
    }
    return config;
  }, [plot.series]);

  const excludedKeys = useMemo(
    () => new Set(plot.series.map((s) => projectMetricKeyString(s))),
    [plot.series]
  );

  const handleAddMetric = (option: MetricNameOption) => {
    const key = projectMetricKeyString(option);
    if (excludedKeys.has(key)) return;
    onPatchPlot(plot.id, {
      series: [
        ...plot.series,
        {
          id: crypto.randomUUID(),
          name: option.name,
          label: option.label,
          color: CHART_COLORS[plot.series.length % CHART_COLORS.length]!,
        },
      ],
    });
  };

  const handleRemoveSeries = (seriesId: string) => {
    onPatchPlot(plot.id, {
      series: plot.series.filter((s) => s.id !== seriesId),
    });
  };

  const handleColorChange = (seriesId: string, color: string) => {
    onPatchPlot(plot.id, {
      series: plot.series.map((s) => (s.id === seriesId ? { ...s, color } : s)),
    });
  };

  return (
    <Card className="min-w-0">
      <CardHeader className="flex flex-row items-center justify-end gap-2 space-y-0 p-1">
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
      <CardContent className="flex min-h-[240px] flex-col gap-2 p-0 pb-1 sm:flex-row">
        <div className="min-h-[220px] min-w-0 flex-1">
          {plot.series.length === 0 ? (
            <div className="flex h-full min-h-[220px] items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
              Add metrics from the panel on the right.
            </div>
          ) : isLoading ? (
            <div className="flex h-full min-h-[220px] items-center justify-center text-sm text-muted-foreground">
              Loading plot…
            </div>
          ) : (
            <ChartContainer
              config={chartConfig}
              className="aspect-auto h-full w-full min-w-0 [&_.recharts-cartesian-axis-tick_text]:text-[11px] [&_.recharts-cartesian-grid_line]:stroke-border/40 [&_.recharts-reference-line_line]:stroke-border/45"
              style={{
                height: chartLayout.chartHeight,
              }}
            >
              <LineChart
                data={chartData}
                margin={{
                  left: chartLayout.chartMarginHorizontal.left,
                  right: chartLayout.chartMarginHorizontal.right,
                  top: 0,
                  bottom: lineChartBottomMargin(chartLayout.xAxisHeight),
                }}
              >
                <CartesianGrid horizontal vertical={false} stroke="#ccc" />
                {chartData.map((point) => (
                  <ReferenceLine
                    key={point.experimentId}
                    x={point.experimentName}
                    stroke="#ccc"
                    strokeOpacity={0.55}
                    ifOverflow="extendDomain"
                  />
                ))}
                <XAxis
                  dataKey="experimentName"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={0}
                  interval={0}
                  angle={nameLabelAngle}
                  textAnchor={xAxisTickTextAnchor(nameLabelAngle)}
                  height={chartLayout.xAxisHeight}
                  padding={chartLayout.xAxisPadding}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tickMargin={0}
                  width={chartLayout.yAxisWidth}
                  tickFormatter={(value) => formatMetricScalarForDisplay(Number(value))}
                />
                <ChartTooltip
                  shared
                  cursor={{ stroke: "#ccc", strokeOpacity: 0.45, strokeWidth: 1 }}
                  content={<ComparePlotTooltipContent chartConfig={chartConfig} />}
                />
                {plot.series.map((s) => (
                  <Line
                    key={s.id}
                    type="monotone"
                    dataKey={s.id}
                    stroke={s.color}
                    strokeWidth={2}
                    dot={{ r: 4, fill: s.color, strokeWidth: 0 }}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ChartContainer>
          )}
        </div>

        <aside className="flex w-full shrink-0 flex-col gap-3 border-t pt-3 sm:w-56 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0">
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Add metric</p>
            <MetricsCompareMetricPicker
              options={metricOptions}
              excludedKeys={excludedKeys}
              onSelect={handleAddMetric}
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor={`plot-name-angle-${plot.id}`} className="text-xs text-muted-foreground">
                Name angle
              </Label>
              <span className="text-xs tabular-nums text-muted-foreground">{nameLabelAngle}°</span>
            </div>
            <Slider
              id={`plot-name-angle-${plot.id}`}
              min={-90}
              max={0}
              step={5}
              value={[nameLabelAngle]}
              onValueChange={([value]) => {
                if (value === undefined) return;
                onPatchPlot(plot.id, { nameLabelAngle: value });
              }}
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor={`plot-point-padding-${plot.id}`} className="text-xs text-muted-foreground">
                Point spacing
              </Label>
              <span className="text-xs tabular-nums text-muted-foreground">{pointPadding}px</span>
            </div>
            <Slider
              id={`plot-point-padding-${plot.id}`}
              min={0}
              max={MAX_COMPARE_PLOT_POINT_PADDING}
              step={4}
              value={[pointPadding]}
              onValueChange={([value]) => {
                if (value === undefined) return;
                onPatchPlot(plot.id, { pointPadding: value });
              }}
            />
          </div>
          <div className="min-h-0 flex-1 space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Series</p>
            {plot.series.length === 0 ? (
              <p className="text-xs text-muted-foreground">No metrics added yet.</p>
            ) : (
              <ul className="max-h-48 space-y-0.5 overflow-y-auto pr-1">
                {plot.series.map((s) => (
                  <li key={s.id} className="flex items-center gap-2 rounded-sm py-1 pr-0.5">
                    <PlotSeriesColorMenu
                      color={s.color}
                      onColorChange={(color) => handleColorChange(s.id, color)}
                    />
                    <span
                      className="min-w-0 flex-1 truncate text-xs"
                      title={formatMetricLabel(s.name, s.label)}
                    >
                      {formatMetricLabel(s.name, s.label)}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 text-muted-foreground"
                      onClick={() => handleRemoveSeries(s.id)}
                      aria-label={`Remove ${formatMetricLabel(s.name, s.label)}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </CardContent>
    </Card>
  );
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

  const experimentName =
    label != null && label !== ""
      ? String(label)
      : String(payload[0]?.payload?.experimentName ?? "");

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
