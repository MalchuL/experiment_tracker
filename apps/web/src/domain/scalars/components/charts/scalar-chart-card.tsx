"use client";

import { EyeOff, Maximize2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
} from "@/domain/scalars/types";
import { MetricChart } from "@/domain/scalars/components/metric-chart";
import { ScalarCardResizeHandle } from "./scalar-card-resize-handle";

interface ScalarChartCardProps {
  metricName: string;
  data: ScalarChartPoint[];
  experiments: {
    allExperiments: Experiment[];
    visibleExperiments: Experiment[];
  };
  size: {
    cardHeight: number;
    cardMinWidth: number;
    onResizeCards: (size: { width: number; height: number }) => void;
  };
  zoom: {
    domain: ChartDomain;
    onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
    onResetDomain: (metricName: string) => void;
  };
  display: {
    smoothing: number;
    dotThreshold: number;
    hoverMode: ScalarHoverMode;
    hoverNameMaxLength: number;
  };
  actions: {
    onExpandMetric: (metricName: string) => void;
    onHideMetric: (metricName: string) => void;
    onHoverModeChange: (mode: ScalarHoverMode) => void;
    onPointContextMenu: (
      point: ScalarPointSelection,
      position: { x: number; y: number },
    ) => void;
  };
  status?: {
    loading?: boolean;
    error?: boolean;
  };
}

export function ScalarChartCard({
  metricName,
  data,
  experiments: { allExperiments, visibleExperiments },
  size: { cardHeight, cardMinWidth, onResizeCards },
  zoom: { domain, onDomainChange, onResetDomain },
  display: { smoothing, dotThreshold, hoverMode, hoverNameMaxLength },
  actions: {
    onExpandMetric,
    onHideMetric,
    onHoverModeChange,
    onPointContextMenu,
  },
  status: { loading = false, error = false } = {},
}: ScalarChartCardProps) {
  const hasData = data.length > 0;

  return (
    <Card
      className="relative gap-0 overflow-hidden rounded-lg py-0"
      data-testid={`card-metric-${metricName}`}
      style={{ width: cardMinWidth, height: cardHeight + 48 }}
    >
      <CardHeader className="px-2.5 py-1.5">
        <CardTitle className="flex items-center justify-between gap-2 text-sm">
          <span className="min-w-0 truncate" title={metricName}>
            {metricName}
          </span>
          <div className="flex shrink-0 items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onResetDomain(metricName)}
              title="Reset zoom"
              data-testid={`button-reset-zoom-${metricName}`}
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onExpandMetric(metricName)}
              title="Expand"
              data-testid={`button-expand-${metricName}`}
            >
              <Maximize2 className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onHideMetric(metricName)}
              title="Hide"
              data-testid={`button-hide-metric-${metricName}`}
            >
              <EyeOff className="h-3 w-3" />
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      {error && hasData ? (
        <span
          role="alert"
          className="absolute bottom-1 left-2 z-10 bg-background text-xs"
        >
          Refresh failed; showing cached data. Use Refresh to retry.
        </span>
      ) : null}
      <CardContent className="px-1.5 pb-2 pt-0">
        {!hasData ? (
          <div
            className="flex items-center justify-center text-sm text-muted-foreground"
            style={{ height: cardHeight }}
          >
            {error
              ? "Could not load scalar. Use Refresh to retry."
              : loading
                ? "Loading scalar…"
                : "No data for selected experiments"}
          </div>
        ) : (
          <MetricChart
            metricName={metricName}
            data={data}
            experiments={{
              selectedExperiments: visibleExperiments,
              allExperiments: allExperiments,
            }}
            viewport={{
              height: cardHeight,
              resizeRevision: cardMinWidth,
            }}
            zoom={{
              domain: domain,
              onDomainChange: (nextDomain) =>
                onDomainChange(metricName, nextDomain),
            }}
            display={{
              smoothing: smoothing,
              dotThreshold: dotThreshold,
              hoverMode: hoverMode,
              hoverNameMaxLength: hoverNameMaxLength,
            }}
            interactions={{
              onHoverModeChange: onHoverModeChange,
              onPointContextMenu: onPointContextMenu,
            }}
          />
        )}
      </CardContent>
      <ScalarCardResizeHandle
        width={cardMinWidth}
        height={cardHeight}
        onResize={onResizeCards}
      />
    </Card>
  );
}
