"use client";

import { useMemo, useState, type KeyboardEvent } from "react";
import { ChevronLeft, ChevronRight, LoaderCircle, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import type { Experiment } from "@/domain/experiments/types";
import { ScalarCardResizeHandle } from "@/domain/scalars/components/charts/scalar-card-resize-handle";
import { MetricChart } from "@/domain/scalars/components/metric-chart";
import { useProjectScalarNames, useProjectScalars } from "@/domain/scalars/hooks";
import type { ChartDomain } from "@/domain/scalars/types";
import { buildChartDataByMetric } from "@/domain/scalars/utils/scalars-data-model";
import { getScalarsDotThreshold } from "@/domain/scalars/utils";
import { cn } from "@/lib/utils";
import { resolveCommittedMaxPoints, resolveCommittedStepBound } from "../lib";
import {
  MAX_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH,
  MAX_SCALAR_COMPARE_PLOT_HEIGHT,
  MIN_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH,
  MIN_SCALAR_COMPARE_PLOT_HEIGHT,
  SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH_STEP,
  type ScalarComparePlotConfig,
  type ScalarMetricOption,
} from "../types";
import { ScalarsCompareScalarPicker } from "./scalars-compare-scalar-picker";

type ScalarsComparePlotCardProps = {
  projectId: string;
  plot: ScalarComparePlotConfig;
  selectedExperiments: Experiment[];
  onPatchPlot: (plotId: string, patch: Partial<ScalarComparePlotConfig>) => void;
  onRemove: () => void;
};

export function ScalarsComparePlotCard({
  projectId,
  plot,
  selectedExperiments,
  onPatchPlot,
  onRemove,
}: ScalarsComparePlotCardProps) {
  const [settingsOpen, setSettingsOpen] = useState(true);
  const experimentIds = useMemo(
    () => selectedExperiments.map((experiment) => experiment.id),
    [selectedExperiments]
  );
  const dotThreshold = useMemo(() => getScalarsDotThreshold(), []);
  const queryStepBounds = useMemo(
    () => resolveQueryStepBounds(plot.stepMin, plot.stepMax),
    [plot.stepMin, plot.stepMax]
  );
  const requestedScalarNames = useMemo(
    () => (plot.metricName ? [plot.metricName] : []),
    [plot.metricName]
  );
  const { scalarNames } = useProjectScalarNames(projectId);

  const {
    scalars,
    isLoading,
    isFetching,
    isFetchingNextPage,
    refetch,
  } = useProjectScalars({
    projectId,
    experimentIds,
    scalarNames: requestedScalarNames,
    maxPoints: plot.appliedMaxPoints,
    returnTags: false,
    storeCache: false,
    startStep: queryStepBounds.startStep,
    endStep: queryStepBounds.endStep,
  });

  const metricOptions = useMemo<ScalarMetricOption[]>(() => {
    return [...scalarNames]
      .sort((a, b) => a.localeCompare(b))
      .map((name) => ({ name, displayName: name }));
  }, [scalarNames]);

  const chartData = useMemo(() => {
    if (!plot.metricName) return [];
    return (
      buildChartDataByMetric({
        scalars,
        allLoggedMetricNames: [plot.metricName],
        visibleExperiments: selectedExperiments,
        smoothing: plot.smoothing,
      })[plot.metricName] ?? []
    );
  }, [plot.metricName, plot.smoothing, scalars, selectedExperiments]);

  const commitMaxPointsDraft = () => {
    const result = resolveCommittedMaxPoints(plot.maxPointsDraft, plot.appliedMaxPoints);
    onPatchPlot(plot.id, {
      maxPointsDraft: result.maxPointsDraft,
      appliedMaxPoints: result.appliedMaxPoints,
    });
  };

  const handleMaxPointsKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
      commitMaxPointsDraft();
    }
  };

  const commitStepMinDraft = () => {
    const result = resolveCommittedStepBound(plot.stepMinDraft, plot.stepMin);
    onPatchPlot(plot.id, {
      stepMinDraft: result.stepBoundDraft,
      stepMin: result.stepBound,
    });
  };

  const commitStepMaxDraft = () => {
    const result = resolveCommittedStepBound(plot.stepMaxDraft, plot.stepMax);
    onPatchPlot(plot.id, {
      stepMaxDraft: result.stepBoundDraft,
      stepMax: result.stepBound,
    });
  };

  const handleStepMinKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
      commitStepMinDraft();
    }
  };

  const handleStepMaxKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.currentTarget.blur();
      commitStepMaxDraft();
    }
  };

  const handleSmoothingChange = (value: number) => {
    onPatchPlot(plot.id, { smoothing: clampSmoothing(value) });
  };

  const handleDomainChange = (domain: ChartDomain | null) => {
    onPatchPlot(plot.id, { domain });
  };

  const metricLabel = plot.metricName ?? "Scalar plot";
  const showLoadingPlaceholder =
    chartData.length === 0 && (isLoading || isFetchingNextPage);

  return (
    <Card className="relative min-w-0 overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 p-2">
        <span className="min-w-0 truncate text-sm font-medium" title={metricLabel}>
          {metricLabel}
        </span>
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
      <CardContent className="flex flex-col gap-2 p-0 pb-2 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1 px-2">
          {!plot.metricName ? (
            <PlotPlaceholder height={plot.plotHeight}>
              Choose a scalar from the panel on the right.
            </PlotPlaceholder>
          ) : showLoadingPlaceholder ? (
            <PlotPlaceholder height={plot.plotHeight}>Loading plot...</PlotPlaceholder>
          ) : chartData.length === 0 ? (
            <PlotPlaceholder height={plot.plotHeight}>
              No data for selected experiments.
            </PlotPlaceholder>
          ) : (
            <MetricChart
              metricName={plot.metricName}
              data={chartData}
              selectedExperiments={selectedExperiments}
              allExperiments={selectedExperiments}
              height={plot.plotHeight}
              resizeRevision={plot.plotHeight}
              domain={plot.domain}
              smoothing={plot.smoothing}
              dotThreshold={dotThreshold}
              hoverMode={plot.hoverMode}
              hoverNameMaxLength={plot.hoverNameMaxLength}
              onDomainChange={handleDomainChange}
              onHoverModeChange={(hoverMode) => onPatchPlot(plot.id, { hoverMode })}
            />
          )}
        </div>

        <PlotSettingsPanel
          plot={plot}
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          metricOptions={metricOptions}
          isFetching={isFetching}
          onPatchPlot={onPatchPlot}
          onRefetch={() => void refetch()}
          onCommitMaxPoints={commitMaxPointsDraft}
          onMaxPointsKeyDown={handleMaxPointsKeyDown}
          onCommitStepMin={commitStepMinDraft}
          onCommitStepMax={commitStepMaxDraft}
          onStepMinKeyDown={handleStepMinKeyDown}
          onStepMaxKeyDown={handleStepMaxKeyDown}
          onSmoothingChange={handleSmoothingChange}
          onResetDomain={() => handleDomainChange(null)}
        />
      </CardContent>
      <ScalarCardResizeHandle
        width={720}
        height={plot.plotHeight}
        onResize={(size) =>
          onPatchPlot(plot.id, {
            plotHeight: size.height,
          })
        }
      />
    </Card>
  );
}

function PlotSettingsPanel({
  plot,
  open,
  onOpenChange,
  metricOptions,
  isFetching,
  onPatchPlot,
  onRefetch,
  onCommitMaxPoints,
  onMaxPointsKeyDown,
  onCommitStepMin,
  onCommitStepMax,
  onStepMinKeyDown,
  onStepMaxKeyDown,
  onSmoothingChange,
  onResetDomain,
}: {
  plot: ScalarComparePlotConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  metricOptions: ScalarMetricOption[];
  isFetching: boolean;
  onPatchPlot: (plotId: string, patch: Partial<ScalarComparePlotConfig>) => void;
  onRefetch: () => void;
  onCommitMaxPoints: () => void;
  onMaxPointsKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onCommitStepMin: () => void;
  onCommitStepMax: () => void;
  onStepMinKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onStepMaxKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onSmoothingChange: (value: number) => void;
  onResetDomain: () => void;
}) {
  return (
    <div
      className={cn(
        "relative shrink-0 transition-[width] duration-300",
        open ? "w-full sm:w-60" : "w-0"
      )}
    >
      {open ? (
        <aside className="flex flex-col gap-3 border-t px-3 pt-3 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-muted-foreground">Plot controls</p>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              onClick={onRefetch}
              disabled={isFetching}
              title="Refetch"
              aria-label="Refetch scalar plot"
            >
              {isFetching ? (
                <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Scalar</p>
            <ScalarsCompareScalarPicker
              options={metricOptions}
              placeholder={plot.metricName ?? "Search scalars..."}
              onSelect={(option) =>
                onPatchPlot(plot.id, { metricName: option.name, domain: null })
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={`scalar-max-points-${plot.id}`} className="text-xs text-muted-foreground">
              Points
            </Label>
            <Input
              id={`scalar-max-points-${plot.id}`}
              type="number"
              min={1}
              step={1}
              className="h-8"
              value={plot.maxPointsDraft}
              onChange={(event) =>
                onPatchPlot(plot.id, { maxPointsDraft: event.target.value })
              }
              onBlur={onCommitMaxPoints}
              onKeyDown={onMaxPointsKeyDown}
            />
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Step range</p>
            <div className="grid grid-cols-2 gap-2">
              <StepBoundField
                id={`scalar-step-min-${plot.id}`}
                label="Min"
                value={plot.stepMinDraft}
                onChange={(stepMinDraft) => onPatchPlot(plot.id, { stepMinDraft })}
                onBlur={onCommitStepMin}
                onKeyDown={onStepMinKeyDown}
              />
              <StepBoundField
                id={`scalar-step-max-${plot.id}`}
                label="Max"
                value={plot.stepMaxDraft}
                onChange={(stepMaxDraft) => onPatchPlot(plot.id, { stepMaxDraft })}
                onBlur={onCommitStepMax}
                onKeyDown={onStepMaxKeyDown}
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor={`scalar-smoothing-${plot.id}`} className="text-xs text-muted-foreground">
                Smoothing
              </Label>
              <Input
                type="number"
                min={0}
                max={0.99}
                step={0.01}
                className="h-7 w-20 text-xs"
                value={plot.smoothing}
                onChange={(event) => onSmoothingChange(Number(event.target.value))}
                aria-label="Smoothing value"
              />
            </div>
            <Slider
              id={`scalar-smoothing-${plot.id}`}
              min={0}
              max={0.99}
              step={0.01}
              value={[plot.smoothing]}
              onValueChange={([nextValue]) => {
                if (nextValue === undefined) return;
                onSmoothingChange(nextValue);
              }}
            />
          </div>

          <PlotSliderField
            id={`scalar-height-${plot.id}`}
            label="Plot height"
            value={plot.plotHeight}
            min={MIN_SCALAR_COMPARE_PLOT_HEIGHT}
            max={MAX_SCALAR_COMPARE_PLOT_HEIGHT}
            step={8}
            valueSuffix="px"
            onChange={(value) => onPatchPlot(plot.id, { plotHeight: value })}
          />

          <PlotSliderField
            id={`scalar-hover-name-${plot.id}`}
            label="Hover name"
            value={plot.hoverNameMaxLength}
            min={MIN_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH}
            max={MAX_SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH}
            step={SCALAR_COMPARE_HOVER_NAME_MAX_LENGTH_STEP}
            valueSuffix=" chars"
            onChange={(value) => onPatchPlot(plot.id, { hoverNameMaxLength: value })}
          />

          <Button type="button" variant="outline" size="sm" onClick={onResetDomain}>
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Reset zoom
          </Button>
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

function StepBoundField({
  id,
  label,
  value,
  onChange,
  onBlur,
  onKeyDown,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        type="number"
        step={1}
        className="h-8"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
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
  valueSuffix,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  valueSuffix: string;
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
          {valueSuffix}
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

function clampSmoothing(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(0.99, Math.max(0, value));
}

function resolveQueryStepBounds(
  stepMin: number | null,
  stepMax: number | null
): { startStep?: number; endStep?: number } {
  if (stepMin !== null && stepMax !== null && stepMin > stepMax) {
    return {};
  }
  return {
    startStep: stepMin ?? undefined,
    endStep: stepMax ?? undefined,
  };
}
