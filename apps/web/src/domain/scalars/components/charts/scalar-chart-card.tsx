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
  domain: ChartDomain;
  cardHeight: number;
  cardMinWidth: number;
  allExperiments: Experiment[];
  visibleExperiments: Experiment[];
  smoothing: number;
  dotThreshold: number;
  hoverMode: ScalarHoverMode;
  hoverNameMaxLength: number;
  onHoverModeChange: (mode: ScalarHoverMode) => void;
  onResetDomain: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onHideMetric: (metricName: string) => void;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  onResizeCards: (size: { width: number; height: number }) => void;
  onPointContextMenu: (point: ScalarPointSelection, position: { x: number; y: number }) => void;
}

export function ScalarChartCard({
  metricName,
  data,
  domain,
  cardHeight,
  cardMinWidth,
  allExperiments,
  visibleExperiments,
  smoothing,
  dotThreshold,
  hoverMode,
  hoverNameMaxLength,
  onHoverModeChange,
  onResetDomain,
  onExpandMetric,
  onHideMetric,
  onDomainChange,
  onResizeCards,
  onPointContextMenu,
}: ScalarChartCardProps) {
  const hasData = data.length > 0;

  return (
    <Card
      className="relative overflow-hidden rounded-lg"
      data-testid={`card-metric-${metricName}`}
      style={{ width: cardMinWidth }}
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
      <CardContent className="px-1.5 pb-2 pt-0">
        {!hasData ? (
          <div
            className="flex items-center justify-center text-sm text-muted-foreground"
            style={{ height: cardHeight }}
          >
            No data for selected experiments
          </div>
        ) : (
          <MetricChart
            metricName={metricName}
            data={data}
            selectedExperiments={visibleExperiments}
            allExperiments={allExperiments}
            height={cardHeight}
            domain={domain}
            smoothing={smoothing}
            dotThreshold={dotThreshold}
            hoverMode={hoverMode}
            hoverNameMaxLength={hoverNameMaxLength}
            onHoverModeChange={onHoverModeChange}
            onPointContextMenu={onPointContextMenu}
            onDomainChange={(nextDomain) => onDomainChange(metricName, nextDomain)}
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
