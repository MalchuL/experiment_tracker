"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import type { Experiment } from "@/domain/experiments/types";
import { getScalarsMaxPointsPerPlot } from "@/domain/scalars/utils";
import {
  loadPersistedScalarComparePlots,
  savePersistedScalarComparePlots,
} from "../lib/persisted-scalar-plots";
import type { ScalarComparePlotConfig } from "../types";
import { ScalarsComparePlotsSection } from "./scalars-compare-plots-section";

export function ScalarsCompareTab({
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
  const defaultMaxPoints = useMemo(() => getScalarsMaxPointsPerPlot(), []);
  const plotStorageScope = `compare:${projectId}`;
  const [plots, setPlots] = useState<ScalarComparePlotConfig[]>(() =>
    loadPersistedScalarComparePlots(plotStorageScope, defaultMaxPoints)
  );
  const latestExperiment = allExperiments[0] ?? null;

  useEffect(() => {
    savePersistedScalarComparePlots(plotStorageScope, plots, defaultMaxPoints);
  }, [defaultMaxPoints, plotStorageScope, plots]);

  if (selectedExperiments.length === 0) {
    return (
      <Centered className="flex-col gap-3 text-center">
        <span>
          Please select an experiment to compare scalars
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

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ScalarsComparePlotsSection
        projectId={projectId}
        selectedExperiments={selectedExperiments}
        plots={plots}
        defaultMaxPoints={defaultMaxPoints}
        onPlotsChange={setPlots}
      />
    </div>
  );
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
