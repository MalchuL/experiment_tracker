"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Experiment } from "@/domain/experiments/types";
import { MetricsComparePlotCard } from "./metrics-compare-plot-chart";
import type { ComparePlotConfig, MetricNameOption } from "../types/metrics-compare";
import {
  DEFAULT_COMPARE_PLOT_NAME_LABEL_ANGLE,
  DEFAULT_COMPARE_PLOT_POINT_PADDING,
  MAX_COMPARE_PLOT_POINT_PADDING,
} from "../types/metrics-compare";

type MetricsComparePlotsSectionProps = {
  projectId: string;
  selectedExperiments: Experiment[];
  metricOptions: MetricNameOption[];
  plots: ComparePlotConfig[];
  onPlotsChange: (plots: ComparePlotConfig[]) => void;
  disabled?: boolean;
  bordered?: boolean;
};

export function MetricsComparePlotsSection({
  projectId,
  selectedExperiments,
  metricOptions,
  plots,
  onPlotsChange,
  disabled = false,
  bordered = false,
}: MetricsComparePlotsSectionProps) {
  const handleAddPlot = () => {
    onPlotsChange([
      ...plots,
      {
        id: crypto.randomUUID(),
        series: [],
        nameLabelAngle: DEFAULT_COMPARE_PLOT_NAME_LABEL_ANGLE,
        pointPadding: DEFAULT_COMPARE_PLOT_POINT_PADDING,
      },
    ]);
  };

  const handleRemovePlot = (plotId: string) => {
    onPlotsChange(plots.filter((plot) => plot.id !== plotId));
  };

  const handlePatchPlot = (plotId: string, patch: Partial<ComparePlotConfig>) => {
    onPlotsChange(
      plots.map((plot) => (plot.id === plotId ? { ...plot, ...patch } : plot))
    );
  };

  return (
    <div className={cn("space-y-3 px-5 py-4", bordered && "border-b")}>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddPlot}
          disabled={disabled}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add plot
        </Button>
        {metricOptions.length === 0 && !disabled ? (
          <span className="text-xs text-muted-foreground">No metrics logged in this project.</span>
        ) : null}
      </div>
      {plots.length > 0 ? (
        <div className="flex flex-col gap-4">
          {plots.map((plot) => (
            <MetricsComparePlotCard
              key={plot.id}
              projectId={projectId}
              plot={plot}
              selectedExperiments={selectedExperiments}
              metricOptions={metricOptions}
              onPatchPlot={handlePatchPlot}
              onRemove={() => handleRemovePlot(plot.id)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
