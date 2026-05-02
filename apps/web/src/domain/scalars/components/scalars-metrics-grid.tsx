"use client";

import { EmptyState } from "@/components/shared/empty-state";
import { BarChart3 } from "lucide-react";
import type { Experiment } from "@/domain/experiments/types";
import type {
  ChartDomain,
  ScalarChartPoint,
  ScalarHoverMode,
  ScalarPointSelection,
} from "@/domain/scalars/types";
import { ScalarChartCard } from "@/domain/scalars/components/charts";

interface MetricItem {
  name: string;
}

export interface ScalarsMetricsGridProps {
  visibleMetrics: MetricItem[];
  chartDataByMetric: Record<string, ScalarChartPoint[]>;
  metricDomains: Record<string, ChartDomain>;
  cardHeight: number;
  cardMinWidth: number;
  smoothing?: number;
  dotThreshold?: number;
  hoverMode?: ScalarHoverMode;
  hoverNameMaxLength?: number;
  allExperiments: Experiment[];
  visibleExperiments: Experiment[];
  onResetDomain: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onHideMetric: (metricName: string) => void;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  onResizeCards?: (size: { width: number; height: number }) => void;
  onHoverModeChange?: (mode: ScalarHoverMode) => void;
  onPointContextMenu?: (point: ScalarPointSelection, position: { x: number; y: number }) => void;
}

export function ScalarsMetricsGrid({
  visibleMetrics,
  chartDataByMetric,
  metricDomains,
  cardHeight,
  cardMinWidth,
  smoothing = 0,
  dotThreshold = 10,
  hoverMode = "compare",
  hoverNameMaxLength = 50,
  allExperiments,
  visibleExperiments,
  onResetDomain,
  onExpandMetric,
  onHideMetric,
  onDomainChange,
  onResizeCards = () => {},
  onHoverModeChange = () => {},
  onPointContextMenu = () => {},
}: ScalarsMetricsGridProps) {
  if (visibleMetrics.length === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No scalars visible"
        description="All scalars are hidden. Click 'Show All' to display them."
      />
    );
  }

  return (
    <div
      className="grid gap-3"
      style={{
        gridTemplateColumns: `repeat(auto-fill, ${cardMinWidth}px)`,
        justifyContent: "start",
      }}
    >
      {visibleMetrics.map((metric) => {
        const data = chartDataByMetric[metric.name] || [];
        const hasData = data.length > 0;
        const domain = metricDomains[metric.name] || { x: null, y: null };

        return (
          <ScalarChartCard
            key={metric.name}
            metricName={metric.name}
            data={hasData ? data : []}
            domain={domain}
            cardHeight={cardHeight}
            cardMinWidth={cardMinWidth}
            allExperiments={allExperiments}
            visibleExperiments={visibleExperiments}
            smoothing={smoothing}
            dotThreshold={dotThreshold}
            hoverMode={hoverMode}
            hoverNameMaxLength={hoverNameMaxLength}
            onHoverModeChange={onHoverModeChange}
            onResetDomain={onResetDomain}
            onExpandMetric={onExpandMetric}
            onHideMetric={onHideMetric}
            onDomainChange={onDomainChange}
            onResizeCards={onResizeCards}
            onPointContextMenu={onPointContextMenu}
          />
        );
      })}
    </div>
  );
}
