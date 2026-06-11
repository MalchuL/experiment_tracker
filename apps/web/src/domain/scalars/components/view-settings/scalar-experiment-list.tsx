"use client";

import { useMemo } from "react";
import { parseISO } from "date-fns";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import type { Experiment } from "@/domain/experiments/types";
import { CHART_COLORS } from "@/domain/scalars/constants";

interface ScalarExperimentListProps {
  experiments: Experiment[];
  selectedExperimentIds: Set<string>;
  soloMode: boolean;
  chosenExperimentId: string | null;
  onSoloExperimentSelect: (id: string) => void;
  onToggleExperiment: (experimentId: string) => void;
  onSelectAllExperiments: () => void;
  onClearAllExperiments: () => void;
  onEditExperiment: (experiment: Experiment) => void;
}

export function ScalarExperimentList({
  experiments,
  selectedExperimentIds,
  soloMode,
  chosenExperimentId,
  onSoloExperimentSelect,
  onToggleExperiment,
  onSelectAllExperiments,
  onClearAllExperiments,
  onEditExperiment,
}: ScalarExperimentListProps) {
  const listExperiments = useMemo(
    () =>
      [...experiments].sort(
        (a, b) => parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime()
      ),
    [experiments]
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {selectedExperimentIds.size}/{experiments.length} selected
        </span>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onSelectAllExperiments}>
            All
          </Button>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onClearAllExperiments}>
            None
          </Button>
        </div>
      </div>
      <div className="h-[calc(100vh-14rem)] min-h-0 overflow-auto">
        <div className="min-w-80 space-y-0.5 pr-3">
          {listExperiments.map((experiment, index) => (
            <div key={experiment.id} className="flex items-center gap-1.5 rounded px-1 py-0.5 hover:bg-muted/50">
              {soloMode ? (
                <button
                  type="button"
                  onClick={() => onSoloExperimentSelect(experiment.id)}
                  className={`h-3 w-3 shrink-0 rounded-full border ${
                    chosenExperimentId === experiment.id
                      ? "border-primary bg-primary"
                      : "border-muted-foreground/50"
                  }`}
                  aria-label={`Choose ${experiment.name} for solo mode`}
                  data-testid={`button-solo-experiment-${index}`}
                />
              ) : null}
              <Checkbox
                id={`exp-${experiment.id}`}
                checked={selectedExperimentIds.has(experiment.id)}
                onCheckedChange={() => onToggleExperiment(experiment.id)}
                data-testid={`checkbox-experiment-${index}`}
              />
              <button
                type="button"
                className="h-4 w-4 shrink-0 rounded-full border border-border"
                style={{ backgroundColor: experiment.color || CHART_COLORS[index % CHART_COLORS.length] }}
                onClick={() => onEditExperiment(experiment)}
                aria-label={`Edit ${experiment.name}`}
              />
              <label
                htmlFor={`exp-${experiment.id}`}
                className="flex-1 cursor-pointer whitespace-nowrap text-xs"
                title={experiment.name}
              >
                {experiment.name}
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
