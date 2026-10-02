"use client";

import { useMemo } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
} from "../types";
import { MemoizedPlot } from "./plotly/stable-plot";
import { MultiHoverTooltip } from "./plotly/metric-chart-tooltip";
import { buildMetricChartTraces } from "./plotly/metric-chart-traces";
import { useMetricChartInteractions } from "../hooks/use-metric-chart-interactions";
import { useMetricChartLayout } from "../hooks/use-metric-chart-layout";
import {
  buildExperimentHoverDisplayNames,
  usesUnifiedMultiHover,
} from "../utils/metric-chart-hover";

export interface MetricChartProps {
  metricName: string;
  data: ScalarChartPoint[];
  experiments: {
    selectedExperiments: Experiment[];
    allExperiments: Experiment[];
  };
  viewport?: {
    height?: number | string;
    resizeRevision?: number;
    isFullscreen?: boolean;
  };
  zoom?: {
    domain?: ChartDomain | null;
    onDomainChange?: (domain: ChartDomain | null) => void;
  };
  display?: {
    smoothing?: number;
    dotThreshold?: number;
    hoverMode?: ScalarHoverMode;
    hoverNameMaxLength?: number;
  };
  interactions?: {
    onHoverModeChange?: (mode: ScalarHoverMode) => void;
    onPointContextMenu?: (
      point: ScalarPointSelection,
      position: { x: number; y: number },
    ) => void;
  };
}

export function MetricChart({
  metricName,
  data,
  experiments: { selectedExperiments, allExperiments },
  viewport: { height = 200, resizeRevision, isFullscreen = false } = {},
  zoom: { domain, onDomainChange } = {},
  display: {
    smoothing = 0,
    dotThreshold = 10,
    hoverMode = "compare",
    hoverNameMaxLength = 50,
  } = {},
  interactions: { onHoverModeChange, onPointContextMenu } = {},
}: MetricChartProps) {
  const hoverDisplayNames = useMemo(
    () =>
      buildExperimentHoverDisplayNames(selectedExperiments, hoverNameMaxLength),
    [selectedExperiments, hoverNameMaxLength],
  );
  const plotData = useMemo(
    () =>
      buildMetricChartTraces({
        metricName,
        data,
        experiments: { selectedExperiments, allExperiments },
        display: { smoothing, dotThreshold, hoverMode, hoverNameMaxLength },
        isFullscreen,
        hoverDisplayNames,
      }),
    [
      metricName,
      data,
      selectedExperiments,
      allExperiments,
      smoothing,
      dotThreshold,
      hoverMode,
      hoverNameMaxLength,
      isFullscreen,
      hoverDisplayNames,
    ],
  );
  const interactions = useMetricChartInteractions({
    zoom: { domain, onDomainChange },
    hover: { hoverMode, hoverDisplayNames },
    onPointContextMenu,
  });
  const { layout, config } = useMetricChartLayout({
    metricName,
    viewport: { height, isFullscreen },
    zoom: { domain, onDomainChange },
    hover: { hoverMode, onHoverModeChange },
    dragMode: interactions.dragMode,
  });

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-muted-foreground"
        style={{ height }}
      >
        No data for selected experiments
      </div>
    );
  }

  return (
    <div
      className="relative"
      style={{ height }}
      onContextMenu={interactions.events.handleContextMenu}
      onPointerLeave={interactions.events.handleUnhover}
    >
      <MemoizedPlot
        data={plotData}
        layout={layout}
        config={config}
        revision={resizeRevision}
        shouldFreezeUpdates={interactions.shouldFreezePlotUpdates}
        onHover={interactions.events.handleHover}
        onUnhover={
          usesUnifiedMultiHover(hoverMode)
            ? undefined
            : interactions.events.handleUnhover
        }
        onRelayout={interactions.events.handleRelayout}
        onInitialized={interactions.events.handleInitialized}
      />
      {usesUnifiedMultiHover(hoverMode) && interactions.multiHover ? (
        <MultiHoverTooltip hover={interactions.multiHover} />
      ) : null}
    </div>
  );
}
