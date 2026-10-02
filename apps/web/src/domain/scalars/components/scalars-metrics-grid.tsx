"use client";

import { VirtualScalarCard } from "./charts/virtual-scalar-card";

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
  experiments: {
    allExperiments: Experiment[];
    visibleExperiments: Experiment[];
  };
  size: {
    cardHeight: number;
    cardMinWidth: number;
    onResizeCards?: (size: { width: number; height: number }) => void;
  };
  zoom: {
    metricDomains: Record<string, ChartDomain>;
    onResetDomain: (metricName: string) => void;
    onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
  };
  display?: {
    smoothing?: number;
    dotThreshold?: number;
    hoverMode?: ScalarHoverMode;
    hoverNameMaxLength?: number;
  };
  actions: {
    onExpandMetric: (metricName: string) => void;
    onHideMetric: (metricName: string) => void;
    onHoverModeChange?: (mode: ScalarHoverMode) => void;
    onPointContextMenu?: (
      point: ScalarPointSelection,
      position: { x: number; y: number },
    ) => void;
  };
  loading?: {
    onMetricVisibilityChange?: (name: string, visible: boolean) => void;
    statusByMetric?: Record<string, { loading: boolean; error: boolean }>;
  };
  metrics: {
    visibleMetrics: MetricItem[];
    chartDataByMetric: Record<string, ScalarChartPoint[]>;
  };
}

export function ScalarsMetricsGrid({
  experiments: { allExperiments, visibleExperiments },
  size: { cardHeight, cardMinWidth, onResizeCards = () => {} },
  zoom: { metricDomains, onResetDomain, onDomainChange },
  display: {
    smoothing = 0,
    dotThreshold = 10,
    hoverMode = "compare",
    hoverNameMaxLength = 50,
  } = {},
  actions: {
    onExpandMetric,
    onHideMetric,
    onHoverModeChange = () => {},
    onPointContextMenu = () => {},
  },
  loading: { onMetricVisibilityChange, statusByMetric } = {},
  metrics: { visibleMetrics, chartDataByMetric },
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
          <VirtualScalarCard
            key={metric.name}
            name={metric.name}
            height={cardHeight + 48}
            width={cardMinWidth}
            onVisibilityChange={onMetricVisibilityChange}
          >
            <ScalarChartCard
              metricName={metric.name}
              data={hasData ? data : []}
              experiments={{
                allExperiments: allExperiments,
                visibleExperiments: visibleExperiments,
              }}
              size={{
                cardHeight: cardHeight,
                cardMinWidth: cardMinWidth,
                onResizeCards: onResizeCards,
              }}
              zoom={{
                domain: domain,
                onDomainChange: onDomainChange,
                onResetDomain: onResetDomain,
              }}
              display={{
                smoothing: smoothing,
                dotThreshold: dotThreshold,
                hoverMode: hoverMode,
                hoverNameMaxLength: hoverNameMaxLength,
              }}
              actions={{
                onExpandMetric: onExpandMetric,
                onHideMetric: onHideMetric,
                onHoverModeChange: onHoverModeChange,
                onPointContextMenu: onPointContextMenu,
              }}
              status={{
                loading: statusByMetric
                  ? (statusByMetric[metric.name]?.loading ?? true)
                  : false,
                error: statusByMetric?.[metric.name]?.error,
              }}
            />
          </VirtualScalarCard>
        );
      })}
    </div>
  );
}
