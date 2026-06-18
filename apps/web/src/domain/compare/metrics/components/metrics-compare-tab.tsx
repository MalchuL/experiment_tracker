"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import {
  ExperimentDataCompareTable,
  type ExperimentDataCompareRow,
  type ExperimentDataDiffStatus,
} from "@/domain/compare/components/experiment-data-compare-table";
import type { Experiment } from "@/domain/experiments/types";
import { useSelectiveProjectMetrics } from "@/domain/experiments/hooks";
import { projectsService } from "@/domain/projects/services";
import { MetricDirection } from "@/domain/metrics/types";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { MetricNameValueDiffRow } from "@/components/shared/metric-name-value-diff-row";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { formatMetricScalarForDisplay, formatMetricSignedDeltaForDisplay } from "@/lib/metrics/metric-value-display";
import { displayMetricKeyEquals, projectMetricKeyString } from "@/lib/metrics/format-metric-label";
import { buildAllLabelsCompareTableData } from "../lib/build-metrics-compare-rows";
import type { ComparePlotConfig } from "../types/metrics-compare";
import { uniqueDimensionsToOptions } from "./metrics-compare-metric-picker";
import { MetricsComparePlotsSection } from "./metrics-compare-plots-section";

export function MetricsCompareTab({
  projectId,
  allExperiments,
  selectedExperiments,
  onEnsureExperimentSelected,
}: {
  projectId: string;
  allExperiments: Experiment[];
  selectedExperiments: Experiment[];
  onEnsureExperimentSelected: (experimentId: string) => void;
}) {
  const experimentIds = selectedExperiments.map((experiment) => experiment.id);
  const latestExperiment = allExperiments[0] ?? null;

  const [plots, setPlots] = useState<ComparePlotConfig[]>([]);

  const { data: uniqueDimensions, isLoading: dimensionsLoading, isError: dimensionsError } =
    useQuery({
      queryKey: [QUERY_KEYS.METRICS.UNIQUE_DIMENSIONS(projectId)],
      queryFn: () => projectsService.getUniqueMetricDimensions(projectId),
      enabled: experimentIds.length > 0,
    });

  const metricKeys = useMemo(
    () => uniqueDimensions?.items ?? [],
    [uniqueDimensions?.items]
  );

  const metricOptions = useMemo(
    () => uniqueDimensionsToOptions(metricKeys),
    [metricKeys]
  );

  const projectMetrics = useMemo(
    () =>
      metricKeys.map((key) => ({
        name: key.name,
        label: key.label,
        direction: MetricDirection.MAXIMIZE,
        aggregation: "last" as const,
      })),
    [metricKeys]
  );

  const { project } = useProject(projectId);

  const metricDirectionsByRowId = useMemo(() => {
    const tracked = project?.metrics?.trackedMetrics ?? [];
    const map = new Map<string, "maximize" | "minimize">();
    for (const key of metricKeys) {
      const trackedMetric = tracked.find((metric) =>
        displayMetricKeyEquals(
          { name: metric.name, label: metric.label ?? null },
          { name: key.name, label: key.label }
        )
      );
      map.set(
        projectMetricKeyString(key),
        trackedMetric?.direction === MetricDirection.MINIMIZE ? "minimize" : "maximize"
      );
    }
    return map;
  }, [metricKeys, project?.metrics?.trackedMetrics]);

  const {
    metricsByExperiment,
    isLoading: metricsLoading,
    isFetching: metricsFetching,
  } = useSelectiveProjectMetrics(projectId, experimentIds, projectMetrics);

  const { columns, rows } = useMemo(() => {
    if (metricKeys.length === 0 || experimentIds.length === 0) {
      return { columns: [], rows: [] };
    }
    return buildAllLabelsCompareTableData(
      metricKeys,
      selectedExperiments,
      metricsByExperiment
    );
  }, [metricKeys, selectedExperiments, metricsByExperiment, experimentIds.length]);

  if (experimentIds.length === 0) {
    return (
      <Centered className="flex-col gap-3 text-center">
        <span>
          Please select an experiment to compare metrics
          {latestExperiment ? ", or choose the latest experiment." : "."}
        </span>
        {latestExperiment ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onEnsureExperimentSelected(latestExperiment.id)}
          >
            Choose {latestExperiment.name}
          </Button>
        ) : null}
      </Centered>
    );
  }

  if (dimensionsLoading) {
    return <Centered>Loading metrics…</Centered>;
  }

  if (dimensionsError || !uniqueDimensions) {
    return <Centered>Failed to load metrics.</Centered>;
  }

  if (metricKeys.length === 0) {
    return <Centered>No logged metrics in this project.</Centered>;
  }

  const tableReady = !metricsLoading && !metricsFetching;

  const tableSection =
    !tableReady ? (
      <Centered>Loading metrics table…</Centered>
    ) : rows.length === 0 ? (
      <Centered>No metrics for the selected experiments.</Centered>
    ) : (
      <ExperimentDataCompareTable
        storageScope={`metrics:${projectId}`}
        leadColumnLabel="Metric"
        columns={columns}
        rows={rows}
        renderValue={(value, referenceValue, status, row) =>
          renderCompareMetricValue(
            value,
            referenceValue,
            status,
            row,
            metricDirectionsByRowId
          )
        }
        valueKey={(value) => String(value)}
        valueTitle={(value, referenceValue, status, row) =>
          metricCompareValueTitle(value, referenceValue, status, row, metricDirectionsByRowId)
        }
        defaultOverflowMode="truncate"
      />
    );

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {plots.length > 0 ? (
        <ResizablePanelGroup
          direction="vertical"
          autoSaveId={`compare-metrics-split:${projectId}`}
          className="min-h-0 flex-1"
        >
          <ResizablePanel defaultSize={45} collapsible collapsedSize={0} className="min-h-0">
            <div className="h-full min-h-0 overflow-y-auto">
              <MetricsComparePlotsSection
                projectId={projectId}
                selectedExperiments={selectedExperiments}
                metricOptions={metricOptions}
                plots={plots}
                onPlotsChange={setPlots}
                disabled={!tableReady}
              />
            </div>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={55} collapsible collapsedSize={0} className="min-h-0">
            <div className="flex h-full min-h-0 flex-col overflow-hidden">{tableSection}</div>
          </ResizablePanel>
        </ResizablePanelGroup>
      ) : (
        <>
          <MetricsComparePlotsSection
            projectId={projectId}
            selectedExperiments={selectedExperiments}
            metricOptions={metricOptions}
            plots={plots}
            onPlotsChange={setPlots}
            disabled={!tableReady}
            bordered
          />
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{tableSection}</div>
        </>
      )}
    </div>
  );
}

function renderCompareMetricValue(
  value: number | undefined,
  referenceValue: number | undefined,
  _status: ExperimentDataDiffStatus,
  row: ExperimentDataCompareRow<number>,
  directionsByRowId: Map<string, "maximize" | "minimize">
) {
  if (value === undefined) {
    return <span className="text-sm text-muted-foreground">—</span>;
  }

  const direction = directionsByRowId.get(row.id) ?? "maximize";
  const canDiff = referenceValue !== undefined;

  return (
    <MetricNameValueDiffRow
      metricName={row.label}
      showName={false}
      value={value}
      parentValue={canDiff ? referenceValue ?? null : null}
      direction={direction}
      showDiff={canDiff}
      colorizeDiffOutcome={false}
      valueDiffClusterOrder="diff-first"
      metricTable={{
        scope: "cell",
        groupHasAnyDiff: canDiff,
      }}
      classNameProps={{
        valueText: "text-sm",
        deltaText: "font-mono text-xs tabular-nums leading-none",
        deltaIcon: "h-3 w-3",
      }}
    />
  );
}

function metricCompareValueTitle(
  value: number | undefined,
  referenceValue: number | undefined,
  _status: ExperimentDataDiffStatus,
  _row: ExperimentDataCompareRow<number>,
  _directionsByRowId: Map<string, "maximize" | "minimize">
): string {
  if (value === undefined) return "Not set";
  const formatted = formatMetricScalarForDisplay(value);
  if (referenceValue === undefined) return formatted;
  return `${formatted} (Δ vs reference: ${formatMetricSignedDeltaForDisplay(value - referenceValue)})`;
}

function Centered({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex min-h-0 flex-1 items-center justify-center p-8 text-sm text-muted-foreground ${className}`}
    >
      {children}
    </div>
  );
}
