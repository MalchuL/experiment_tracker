"use client";

import { EyeOff, Maximize2, RotateCcw } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3 } from "lucide-react";
import type { Experiment } from "@/domain/experiments/types";
import type { ChartDomain } from "@/domain/scalars/types";
import { MetricChart } from "@/domain/scalars/components/metric-chart";

interface MetricItem {
  name: string;
}

export interface ScalarsMetricsGridProps {
  visibleMetrics: MetricItem[];
  chartDataByMetric: Record<string, Array<Record<string, number | null>>>;
  metricDomains: Record<string, ChartDomain>;
  cardHeight: number;
  cardMinWidth: number;
  allExperiments: Experiment[];
  visibleExperiments: Experiment[];
  onResetDomain: (metricName: string) => void;
  onExpandMetric: (metricName: string) => void;
  onHideMetric: (metricName: string) => void;
  onDomainChange: (metricName: string, domain: ChartDomain | null) => void;
}

export function ScalarsMetricsGrid({
  visibleMetrics,
  chartDataByMetric,
  metricDomains,
  cardHeight,
  cardMinWidth,
  allExperiments,
  visibleExperiments,
  onResetDomain,
  onExpandMetric,
  onHideMetric,
  onDomainChange,
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
      className="grid gap-4"
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
          <Card key={metric.name} data-testid={`card-metric-${metric.name}`}>
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-sm flex items-center justify-between gap-2">
                <span className="truncate">{metric.name}</span>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => onResetDomain(metric.name)}
                    title="Reset zoom"
                    data-testid={`button-reset-zoom-${metric.name}`}
                  >
                    <RotateCcw className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => onExpandMetric(metric.name)}
                    title="Expand"
                    data-testid={`button-expand-${metric.name}`}
                  >
                    <Maximize2 className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => onHideMetric(metric.name)}
                    title="Hide"
                    data-testid={`button-hide-metric-${metric.name}`}
                  >
                    <EyeOff className="w-3 h-3" />
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-2 pb-2 pt-0">
              {!hasData ? (
                <div
                  className="flex items-center justify-center text-sm text-muted-foreground"
                  style={{ height: cardHeight }}
                >
                  No data for selected experiments
                </div>
              ) : (
                <MetricChart
                  data={data}
                  selectedExperiments={visibleExperiments}
                  allExperiments={allExperiments}
                  height={cardHeight}
                  domain={domain}
                  onDomainChange={(nextDomain) => onDomainChange(metric.name, nextDomain)}
                />
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
