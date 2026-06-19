"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Experiment } from "@/domain/experiments/types";
import { createScalarComparePlotConfig, patchScalarComparePlotConfig } from "../lib";
import type { ScalarComparePlotConfig } from "../types";
import { ScalarsComparePlotCard } from "./scalars-compare-plot-card";

type ScalarsComparePlotsSectionProps = {
  projectId: string;
  selectedExperiments: Experiment[];
  plots: ScalarComparePlotConfig[];
  defaultMaxPoints: number;
  onPlotsChange: (plots: ScalarComparePlotConfig[]) => void;
};

export function ScalarsComparePlotsSection({
  projectId,
  selectedExperiments,
  plots,
  defaultMaxPoints,
  onPlotsChange,
}: ScalarsComparePlotsSectionProps) {
  const handleAddPlot = () => {
    onPlotsChange([...plots, createScalarComparePlotConfig(defaultMaxPoints)]);
  };

  const handleRemovePlot = (plotId: string) => {
    onPlotsChange(plots.filter((plot) => plot.id !== plotId));
  };

  const handlePatchPlot = (plotId: string, patch: Partial<ScalarComparePlotConfig>) => {
    onPlotsChange(patchScalarComparePlotConfig(plots, plotId, patch));
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b px-5 py-4">
        <Button type="button" variant="outline" size="sm" onClick={handleAddPlot}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add plot
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {plots.length > 0 ? (
          <div className="flex flex-col gap-4">
            {plots.map((plot) => (
              <ScalarsComparePlotCard
                key={plot.id}
                projectId={projectId}
                plot={plot}
                selectedExperiments={selectedExperiments}
                onPatchPlot={handlePatchPlot}
                onRemove={() => handleRemovePlot(plot.id)}
              />
            ))}
          </div>
        ) : (
          <div className="flex min-h-48 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            Add a scalar plot to compare selected experiments.
          </div>
        )}
      </div>
    </div>
  );
}
