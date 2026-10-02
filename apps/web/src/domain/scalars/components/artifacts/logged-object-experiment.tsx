"use client";

import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { CHART_COLORS } from "../../constants";
import { closestStep } from "../../utils";
import { API_ROUTES } from "@/lib/constants/api-routes";
import { useArtifactDetail } from "@/domain/logged-objects/hooks/use-artifact-detail";
import { ArtifactMedia } from "./artifact-media";
import type { Experiment } from "@/domain/experiments/types";
import type { LoggedObjectNameGroup, LoggedObjectRef } from "../../types";
import type { LoggedObjectsSectionProps } from "../logged-objects-section";

interface LoggedObjectExperimentProps {
  projectId: string;
  object: {
    selectionKey: string;
    objectType: string;
    name: string;
    group: LoggedObjectNameGroup;
  };
  experiment: { data: Experiment; index: number };
  step: { selectedStep: number; debouncedSelectedStep: number };
  overrides: LoggedObjectsSectionProps["overrides"];
  cardHeight: number;
  onImagePreview: LoggedObjectsSectionProps["onImagePreview"];
}

export function LoggedObjectExperiment({
  projectId,
  object: { selectionKey, objectType, name, group },
  experiment: { data: experiment, index: idx },
  step: { selectedStep, debouncedSelectedStep },
  overrides: {
    experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled,
    enableExperimentStepOverride,
    experimentStepOverrides,
    updateExperimentStepOverride,
    debouncedExperimentStepOverrides,
  },
  cardHeight,
  onImagePreview,
}: LoggedObjectExperimentProps) {
  const experimentOverrideKey = `${selectionKey}:${experiment.id}`;
  const isOverrideEnabled =
    experimentStepOverrideEnabled[experimentOverrideKey] ?? false;
  const experimentColor =
    experiment.color || CHART_COLORS[idx % CHART_COLORS.length];
  const experimentStepMap = group.byExperiment[experiment.id] ?? {};
  const experimentSteps = Object.keys(experimentStepMap)
    .map((step) => Number(step))
    .filter((step) => Number.isFinite(step))
    .sort((a, b) => a - b);
  const overrideFetchDefault =
    closestStep(debouncedSelectedStep, experimentSteps) ??
    experimentSteps[experimentSteps.length - 1] ??
    debouncedSelectedStep;
  const targetStep = isOverrideEnabled
    ? (debouncedExperimentStepOverrides[experimentOverrideKey] ??
      overrideFetchDefault)
    : debouncedSelectedStep;
  const nearestStep = closestStep(targetStep, experimentSteps);
  const objectAtStep =
    nearestStep === null ? undefined : experimentStepMap[nearestStep];
  const currentOverrideIndex = Math.max(
    0,
    experimentSteps.findIndex(
      (step) =>
        step ===
        closestStep(
          experimentStepOverrides[experimentOverrideKey] ?? selectedStep,
          experimentSteps,
        ),
    ),
  );
  return (
    <div className="space-y-1 py-1.5">
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
                  followLatest,
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
              maxOverrideIndex <= 0 || idxValue >= maxOverrideIndex,
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
    objectType,
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
