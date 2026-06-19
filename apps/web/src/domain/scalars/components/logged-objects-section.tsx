"use client";

import { useMemo } from "react";
import { parseISO } from "date-fns";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import type { Dispatch, SetStateAction } from "react";
import type { Experiment } from "@/domain/experiments/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { CHART_COLORS } from "@/domain/scalars/constants";
import { useArtifactDetail } from "@/domain/logged-objects/hooks/use-artifact-detail";
import type {
  LoggedObjectGroups,
  LoggedObjectNameGroup,
  LoggedObjectRef,
} from "@/domain/scalars/types";
import { closestStep } from "@/domain/scalars/utils";
import { ArtifactMedia } from "@/domain/scalars/components/artifacts";

export interface LoggedObjectsSectionProps {
  projectId: string;
  objectGroups: LoggedObjectGroups;
  visibleExperiments: Experiment[];
  cardMinWidth: number;
  cardHeight: number;
  objectStepSelection: Record<string, number>;
  updateObjectStep: (selectionKey: string, step: number, followLatest: boolean) => void;
  debouncedObjectStepSelection: Record<string, number>;
  experimentStepOverrideEnabled: Record<string, boolean>;
  setExperimentStepOverrideEnabled: Dispatch<SetStateAction<Record<string, boolean>>>;
  enableExperimentStepOverride: (overrideKey: string, step: number, followLatest?: boolean) => void;
  experimentStepOverrides: Record<string, number>;
  updateExperimentStepOverride: (overrideKey: string, step: number, followLatest: boolean) => void;
  debouncedExperimentStepOverrides: Record<string, number>;
  onImagePreview: (payload: { src: string; title: string }) => void;
  hiddenArtifactIds?: Set<string>;
  onlyArtifactId?: string | null;
  artifactType?: string;
  artifactNames?: string[];
  showSectionHeader?: boolean;
}

export function LoggedObjectsSection({
  projectId,
  objectGroups,
  visibleExperiments,
  cardMinWidth,
  cardHeight,
  objectStepSelection,
  updateObjectStep,
  debouncedObjectStepSelection,
  experimentStepOverrideEnabled,
  setExperimentStepOverrideEnabled,
  enableExperimentStepOverride,
  experimentStepOverrides,
  updateExperimentStepOverride,
  debouncedExperimentStepOverrides,
  onImagePreview,
  hiddenArtifactIds = new Set(),
  onlyArtifactId = null,
  artifactType,
  artifactNames,
  showSectionHeader = true,
}: LoggedObjectsSectionProps) {
  const artifactExperiments = useMemo(
    () =>
      [...visibleExperiments].sort(
        (a, b) => parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime()
      ),
    [visibleExperiments]
  );

  const typeEntries = useMemo(() => {
    const entries = Object.entries(objectGroups as LoggedObjectGroups);
    if (!artifactType) {
      return entries;
    }
    const byName = objectGroups[artifactType];
    return byName ? [[artifactType, byName] as const] : [];
  }, [artifactType, objectGroups]);

  if (typeEntries.length === 0) return null;

  return (
    <div className={showSectionHeader ? "mt-4 space-y-4" : "space-y-4"}>
      {showSectionHeader ? (
        <div>
          <h2 className="text-base font-semibold">Logged Objects</h2>
          <p className="text-sm text-muted-foreground">
            Objects are grouped by type and name; each card shows one object per selected experiment at the chosen step.
          </p>
        </div>
      ) : null}
      {typeEntries.map(([objectType, byName]) => (
        <div key={objectType} className="space-y-2">
          {showSectionHeader && !artifactType ? (
            <h3 className="text-sm font-medium capitalize">{objectType.replaceAll("_", " ")}</h3>
          ) : null}
          <div
            className="grid gap-3"
            style={{
              gridTemplateColumns: `repeat(auto-fill, ${cardMinWidth}px)`,
              justifyContent: "start",
            }}
          >
            {Object.entries(byName).map(([name, group]: [string, LoggedObjectNameGroup]) => {
              const selectionKey = `${objectType}:${name}`;
              if (artifactNames && !artifactNames.includes(name)) {
                return null;
              }
              if (hiddenArtifactIds.has(selectionKey) || (onlyArtifactId && onlyArtifactId !== selectionKey)) {
                return null;
              }
              const availableSteps = group.steps;
              const defaultStep = availableSteps[availableSteps.length - 1] ?? 0;
              const selectedStep = objectStepSelection[selectionKey] ?? defaultStep;
              const debouncedSelectedStep =
                debouncedObjectStepSelection[selectionKey] ?? defaultStep;
              const maxStepIndex = Math.max(0, availableSteps.length - 1);
              const currentIndex = Math.max(
                0,
                availableSteps.findIndex((step) => step === selectedStep)
              );
              return (
                <Card key={selectionKey} className="border-0 shadow-none">
                  <CardHeader className="px-2.5 py-1.5">
                    <CardTitle className="text-sm flex items-center justify-between gap-2">
                      <span className="truncate">{name}</span>
                      <span className="text-xs text-muted-foreground">step {selectedStep}</span>
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
                        updateObjectStep(selectionKey, step, maxStepIndex <= 0 || idx >= maxStepIndex);
                      }}
                    />
                    <div className="divide-y divide-border" style={{ minHeight: cardHeight }}>
                      {artifactExperiments.map((experiment, idx) => {
                        const experimentOverrideKey = `${selectionKey}:${experiment.id}`;
                        const isOverrideEnabled = experimentStepOverrideEnabled[experimentOverrideKey] ?? false;
                        const experimentColor = experiment.color || CHART_COLORS[idx % CHART_COLORS.length];
                        const experimentStepMap = group.byExperiment[experiment.id] ?? {};
                        const experimentSteps = Object.keys(experimentStepMap)
                          .map((step) => Number(step))
                          .filter((step) => Number.isFinite(step))
                          .sort((a, b) => a - b);
                        const overrideRawStep = experimentStepOverrides[experimentOverrideKey] ?? selectedStep;
                        const overrideFetchDefault =
                          closestStep(debouncedSelectedStep, experimentSteps) ??
                          experimentSteps[experimentSteps.length - 1] ??
                          debouncedSelectedStep;
                        const targetStep = isOverrideEnabled
                          ? debouncedExperimentStepOverrides[experimentOverrideKey] ?? overrideFetchDefault
                          : debouncedSelectedStep;
                        const nearestStep = closestStep(targetStep, experimentSteps);
                        const objectAtStep =
                          nearestStep === null ? undefined : experimentStepMap[nearestStep];
                        const currentOverrideIndex = Math.max(
                          0,
                          experimentSteps.findIndex(
                            (step) =>
                              step === closestStep(experimentStepOverrides[experimentOverrideKey] ?? selectedStep, experimentSteps)
                          )
                        );
                        return (
                          <div key={`${selectionKey}:${experiment.id}`} className="space-y-1 py-1.5">
                            <div className="flex min-w-0 items-center gap-1.5">
                              <span
                                className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                                style={{ backgroundColor: experimentColor }}
                              />
                              <span
                                className="min-w-0 flex-1 truncate text-xs font-medium"
                                title={experiment.name}
                              >
                                {experiment.name}
                              </span>
                              {nearestStep !== null ? (
                                <span
                                  className="shrink-0 cursor-default text-[10px] tabular-nums text-muted-foreground"
                                  title="Closest step this experiment logged for the step chosen on the slider."
                                >
                                  step {nearestStep}
                                </span>
                              ) : null}
                              <span
                                className="shrink-0"
                                title="Choose a step for this experiment independently of the card slider."
                              >
                                <Switch
                                  id={`override-${experimentOverrideKey}`}
                                  checked={isOverrideEnabled}
                                  className="h-4 w-7 shrink-0 [&>span]:h-3 [&>span]:w-3 [&>span]:data-[state=checked]:translate-x-3"
                                  aria-label="Override step"
                                  onCheckedChange={(checked) => {
                                    if (checked === true) {
                                      const latestStep = experimentSteps[experimentSteps.length - 1];
                                      const initialStep =
                                        closestStep(selectedStep, experimentSteps) ?? selectedStep;
                                      const followLatest =
                                        latestStep !== undefined && initialStep === latestStep;
                                      enableExperimentStepOverride(
                                        experimentOverrideKey,
                                        initialStep,
                                        followLatest
                                      );
                                      return;
                                    }
                                    setExperimentStepOverrideEnabled((prev) => ({
                                      ...prev,
                                      [experimentOverrideKey]: false,
                                    }));
                                  }}
                                />
                              </span>
                            </div>
                            {isOverrideEnabled && experimentSteps.length > 0 ? (
                              <Slider
                                value={[currentOverrideIndex]}
                                min={0}
                                max={Math.max(0, experimentSteps.length - 1)}
                                step={1}
                                markCount={experimentSteps.length}
                                onValueChange={(value) => {
                                  const idxValue = value[0] ?? 0;
                                  const maxOverrideIndex = Math.max(0, experimentSteps.length - 1);
                                  const stepValue = experimentSteps[idxValue] ?? experimentSteps[0];
                                  updateExperimentStepOverride(
                                    experimentOverrideKey,
                                    stepValue,
                                    maxOverrideIndex <= 0 || idxValue >= maxOverrideIndex
                                  );
                                }}
                              />
                            ) : null}
                            {!objectAtStep || nearestStep === null ? (
                              <p className="text-xs text-muted-foreground">No object for this step</p>
                            ) : (
                              <LoggedObjectArtifactMedia
                                projectId={projectId}
                                experimentId={experiment.id}
                                experimentName={experiment.name}
                                objectType={objectType}
                                name={name}
                                step={nearestStep}
                                objectRef={objectAtStep}
                                maxHeight={Math.max(120, cardHeight - 50)}
                                onImagePreview={onImagePreview}
                              />
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

function LoggedObjectArtifactMedia({
  projectId,
  experimentId,
  experimentName,
  objectType,
  name,
  step,
  objectRef,
  maxHeight,
  onImagePreview,
}: {
  projectId: string;
  experimentId: string;
  experimentName: string;
  objectType: string;
  name: string;
  step: number;
  objectRef: LoggedObjectRef;
  maxHeight: number;
  onImagePreview: (payload: { src: string; title: string }) => void;
}) {
  /**
   * The download endpoint resolves the object by experiment/name/step/type, so the UI does not
   * need a full metadata row here. The summary's lastModified value is enough to refresh media URLs
   * when the same artifact step is overwritten.
   */
  const baseSrc = API_ROUTES.EXPERIMENT_ARTIFACTS.DOWNLOAD_AT_STEP(
    experimentId,
    step,
    name,
    objectType
  );
  const objectSrc = objectRef.lastModified
    ? `${baseSrc}&cb=${encodeURIComponent(objectRef.lastModified)}`
    : baseSrc;
  const { artifact } = useArtifactDetail({
    projectId,
    experimentId,
    objectType,
    name,
    step,
    enabled: objectType === "histogram" || objectType === "scatter",
  });

  return (
    <ArtifactMedia
      objectType={objectType}
      src={objectSrc}
      name={name}
      experimentName={experimentName}
      maxHeight={maxHeight}
      onImagePreview={onImagePreview}
      title={`${name} · ${experimentName} · step ${step}`}
      metadata={artifact?.metadata}
    />
  );
}
