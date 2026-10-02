"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import type { LoggedObjectNameGroup } from "../../types";
import type { LoggedObjectsSectionProps } from "../logged-objects-section";
import { LoggedObjectExperiment } from "./logged-object-experiment";

type LoggedObjectCardProps = Pick<
  LoggedObjectsSectionProps,
  "projectId" | "size" | "steps" | "overrides" | "onImagePreview"
> & {
  object: { objectType: string; name: string; group: LoggedObjectNameGroup };
  experiments: LoggedObjectsSectionProps["visibleExperiments"];
};

export function LoggedObjectCard({
  projectId,
  object: { objectType, name, group },
  experiments,
  size: { cardHeight },
  steps: {
    objectStepSelection,
    updateObjectStep,
    debouncedObjectStepSelection,
  },
  overrides,
  onImagePreview,
}: LoggedObjectCardProps) {
  const selectionKey = `${objectType}:${name}`;
  const availableSteps = group.steps;
  const defaultStep = availableSteps[availableSteps.length - 1] ?? 0;
  const selectedStep = objectStepSelection[selectionKey] ?? defaultStep;
  const debouncedSelectedStep =
    debouncedObjectStepSelection[selectionKey] ?? defaultStep;
  const maxStepIndex = Math.max(0, availableSteps.length - 1);
  const currentIndex = Math.max(
    0,
    availableSteps.findIndex((step) => step === selectedStep),
  );
  return (
    <Card className="border-0 shadow-none">
      <CardHeader className="px-2.5 py-1.5">
        <CardTitle className="text-sm flex items-center justify-between gap-2">
          <span className="truncate">{name}</span>
          <span className="text-xs text-muted-foreground">
            step {selectedStep}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 px-2 pb-2 pt-0">
        <Slider
          value={[currentIndex]}
          min={0}
          max={maxStepIndex}
          step={1}
          markCount={availableSteps.length}
          disabled={availableSteps.length <= 1}
          onValueChange={(value) => {
            const idx = value[0] ?? 0;
            const step = availableSteps[idx] ?? availableSteps[0] ?? 0;
            updateObjectStep(
              selectionKey,
              step,
              maxStepIndex <= 0 || idx >= maxStepIndex,
            );
          }}
        />
        <div
          className="divide-y divide-border"
          style={{ minHeight: cardHeight }}
        >
          {experiments.map((experiment, index) => (
            <LoggedObjectExperiment
              key={experiment.id}
              projectId={projectId}
              object={{ selectionKey, objectType, name, group }}
              experiment={{ data: experiment, index }}
              step={{ selectedStep, debouncedSelectedStep }}
              overrides={overrides}
              cardHeight={cardHeight}
              onImagePreview={onImagePreview}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
