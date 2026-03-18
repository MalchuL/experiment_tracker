"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import type { Dispatch, SetStateAction } from "react";
import type { Experiment } from "@/domain/experiments/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { CHART_COLORS } from "@/domain/scalars/constants";
import type { LoggedObjectGroups, LoggedObjectNameGroup } from "@/domain/scalars/types";
import { closestStep } from "@/domain/scalars/utils";

export interface LoggedObjectsSectionProps {
  objectGroups: LoggedObjectGroups;
  visibleExperiments: Experiment[];
  cardMinWidth: number;
  cardHeight: number;
  objectStepSelection: Record<string, number>;
  setObjectStepSelection: Dispatch<SetStateAction<Record<string, number>>>;
  debouncedObjectStepSelection: Record<string, number>;
  experimentStepOverrideEnabled: Record<string, boolean>;
  setExperimentStepOverrideEnabled: Dispatch<SetStateAction<Record<string, boolean>>>;
  experimentStepOverrides: Record<string, number>;
  setExperimentStepOverrides: Dispatch<SetStateAction<Record<string, number>>>;
  debouncedExperimentStepOverrides: Record<string, number>;
  onImagePreview: (payload: { src: string; title: string }) => void;
}

export function LoggedObjectsSection({
  objectGroups,
  visibleExperiments,
  cardMinWidth,
  cardHeight,
  objectStepSelection,
  setObjectStepSelection,
  debouncedObjectStepSelection,
  experimentStepOverrideEnabled,
  setExperimentStepOverrideEnabled,
  experimentStepOverrides,
  setExperimentStepOverrides,
  debouncedExperimentStepOverrides,
  onImagePreview,
}: LoggedObjectsSectionProps) {
  if (Object.keys(objectGroups).length === 0) return null;

  return (
    <div className="mt-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Logged Objects</h2>
        <p className="text-sm text-muted-foreground">
          Objects are grouped by type and name; each card shows one object per selected experiment at the chosen step.
        </p>
      </div>
      {Object.entries(objectGroups as LoggedObjectGroups).map(([objectType, byName]) => (
        <div key={objectType} className="space-y-3">
          <h3 className="text-base font-medium capitalize">{objectType.replaceAll("_", " ")}</h3>
          <div
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(auto-fill, ${cardMinWidth}px)`,
              justifyContent: "start",
            }}
          >
            {Object.entries(byName).map(([name, group]: [string, LoggedObjectNameGroup]) => {
              const selectionKey = `${objectType}:${name}`;
              const availableSteps = group.steps;
              const selectedStep = objectStepSelection[selectionKey] ?? availableSteps[availableSteps.length - 1] ?? 0;
              const debouncedSelectedStep = debouncedObjectStepSelection[selectionKey] ?? selectedStep;
              const currentIndex = Math.max(
                0,
                availableSteps.findIndex((step) => step === selectedStep)
              );
              return (
                <Card key={selectionKey}>
                  <CardHeader className="py-2 px-3">
                    <CardTitle className="text-sm flex items-center justify-between gap-2">
                      <span className="truncate">{name}</span>
                      <span className="text-xs text-muted-foreground">step {selectedStep}</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Slider
                      value={[currentIndex]}
                      min={0}
                      max={Math.max(0, availableSteps.length - 1)}
                      step={1}
                      disabled={availableSteps.length <= 1}
                      onValueChange={(value) => {
                        const idx = value[0] ?? 0;
                        const step = availableSteps[idx] ?? availableSteps[0] ?? 0;
                        setObjectStepSelection((prev) => ({
                          ...prev,
                          [selectionKey]: step,
                        }));
                      }}
                    />
                    <div className="space-y-2" style={{ minHeight: cardHeight }}>
                      {visibleExperiments.map((experiment, idx) => {
                        const experimentOverrideKey = `${selectionKey}:${experiment.id}`;
                        const isOverrideEnabled = experimentStepOverrideEnabled[experimentOverrideKey] ?? false;
                        const experimentColor = experiment.color || CHART_COLORS[idx % CHART_COLORS.length];
                        const experimentStepMap = group.byExperiment[experiment.id] ?? {};
                        const experimentSteps = Object.keys(experimentStepMap)
                          .map((step) => Number(step))
                          .filter((step) => Number.isFinite(step))
                          .sort((a, b) => a - b);
                        const overrideRawStep = experimentStepOverrides[experimentOverrideKey] ?? selectedStep;
                        const targetStep = isOverrideEnabled
                          ? debouncedExperimentStepOverrides[experimentOverrideKey] ?? overrideRawStep
                          : debouncedSelectedStep;
                        const nearestStep = closestStep(targetStep, experimentSteps);
                        const objectAtStep = nearestStep === null ? undefined : experimentStepMap[nearestStep];
                        const objectSrc = objectAtStep
                          ? API_ROUTES.EXPERIMENT_ARTIFACTS.DOWNLOAD_AT_STEP(
                              experiment.id,
                              objectAtStep.path,
                              objectAtStep.metadata?.content_type
                            )
                          : "";
                        const currentOverrideIndex = Math.max(
                          0,
                          experimentSteps.findIndex(
                            (step) =>
                              step === closestStep(experimentStepOverrides[experimentOverrideKey] ?? selectedStep, experimentSteps)
                          )
                        );
                        return (
                          <div key={`${selectionKey}:${experiment.id}`} className="rounded border p-2 space-y-1">
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: experimentColor }}
                              />
                              <span className="text-xs font-medium truncate">{experiment.name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={`override-${experimentOverrideKey}`}
                                checked={isOverrideEnabled}
                                onCheckedChange={(checked) => {
                                  const enabled = checked === true;
                                  setExperimentStepOverrideEnabled((prev) => ({
                                    ...prev,
                                    [experimentOverrideKey]: enabled,
                                  }));
                                  if (enabled) {
                                    setExperimentStepOverrides((prev) => ({
                                      ...prev,
                                      [experimentOverrideKey]: prev[experimentOverrideKey] ?? selectedStep,
                                    }));
                                  }
                                }}
                              />
                              <Label htmlFor={`override-${experimentOverrideKey}`} className="text-xs">
                                Override step
                              </Label>
                            </div>
                            {isOverrideEnabled && experimentSteps.length > 0 && (
                              <div className="space-y-1">
                                <Slider
                                  value={[currentOverrideIndex]}
                                  min={0}
                                  max={Math.max(0, experimentSteps.length - 1)}
                                  step={1}
                                  onValueChange={(value) => {
                                    const idxValue = value[0] ?? 0;
                                    const stepValue = experimentSteps[idxValue] ?? experimentSteps[0];
                                    setExperimentStepOverrides((prev) => ({
                                      ...prev,
                                      [experimentOverrideKey]: stepValue,
                                    }));
                                  }}
                                />
                                <p className="text-[10px] text-muted-foreground">
                                  override step {experimentStepOverrides[experimentOverrideKey] ?? selectedStep}
                                </p>
                              </div>
                            )}
                            {!objectAtStep ? (
                              <p className="text-xs text-muted-foreground">No object for this step</p>
                            ) : objectType === "image" ? (
                              <button
                                type="button"
                                className="w-full"
                                onClick={() =>
                                  onImagePreview({
                                    src: objectSrc,
                                    title: `${name} · ${experiment.name} · step ${nearestStep ?? targetStep}`,
                                  })
                                }
                              >
                                <img
                                  src={objectSrc}
                                  alt={`${name}-${experiment.name}`}
                                  className="w-full max-h-40 object-contain rounded"
                                />
                              </button>
                            ) : objectType === "video" ? (
                              <video src={objectSrc} controls className="w-full max-h-40 rounded" />
                            ) : objectType === "audio" ? (
                              <audio src={objectSrc} controls className="w-full" />
                            ) : objectType === "text" ? (
                              <a
                                href={objectSrc}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-primary underline"
                              >
                                Open logged text
                              </a>
                            ) : (
                              <a
                                href={objectSrc}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-primary underline"
                              >
                                Open logged object
                              </a>
                            )}
                            {nearestStep !== null && (
                              <p className="text-[10px] text-muted-foreground">closest step {nearestStep}</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
