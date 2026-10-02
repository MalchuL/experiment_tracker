"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Dispatch, SetStateAction } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type { LoggedObjectGroups } from "../../types";
import { LoggedObjectsSection } from "../logged-objects-section";

export interface ArtifactFullscreenDialogProps {
  selection: {
    fullscreenArtifactId: string | null;
    setFullscreenArtifactId: (artifactId: string | null) => void;
  };
  data: {
    projectId: string;
    objectGroups: LoggedObjectGroups;
  };
  size: {
    cardMinWidth: number;
    cardHeight: number;
  };
  steps: {
    objectStepSelection: Record<string, number>;
    updateObjectStep: (
      selectionKey: string,
      step: number,
      followLatest: boolean,
    ) => void;
    debouncedObjectStepSelection: Record<string, number>;
  };
  overrides: {
    experimentStepOverrideEnabled: Record<string, boolean>;
    setExperimentStepOverrideEnabled: Dispatch<
      SetStateAction<Record<string, boolean>>
    >;
    enableExperimentStepOverride: (
      overrideKey: string,
      step: number,
      followLatest?: boolean,
    ) => void;
    experimentStepOverrides: Record<string, number>;
    updateExperimentStepOverride: (
      overrideKey: string,
      step: number,
      followLatest: boolean,
    ) => void;
    debouncedExperimentStepOverrides: Record<string, number>;
  };
  visibleExperiments: Experiment[];
  onImagePreview: (value: { src: string; title: string }) => void;
}

export function ArtifactFullscreenDialog({
  selection: { fullscreenArtifactId, setFullscreenArtifactId },
  data: { projectId, objectGroups },
  size: { cardMinWidth, cardHeight },
  steps: {
    objectStepSelection,
    updateObjectStep,
    debouncedObjectStepSelection,
  },
  overrides: {
    experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled,
    enableExperimentStepOverride,
    experimentStepOverrides,
    updateExperimentStepOverride,
    debouncedExperimentStepOverrides,
  },
  visibleExperiments,
  onImagePreview,
}: ArtifactFullscreenDialogProps) {
  return (
    <Dialog
      open={!!fullscreenArtifactId}
      onOpenChange={(open) => !open && setFullscreenArtifactId(null)}
    >
      <DialogContent className="max-w-[96vw] w-[96vw] h-[86vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>Artifact view</DialogTitle>
        </DialogHeader>
        {fullscreenArtifactId ? (
          <LoggedObjectsSection
            projectId={projectId}
            objectGroups={objectGroups}
            visibleExperiments={visibleExperiments}
            onImagePreview={onImagePreview}
            size={{
              cardMinWidth: Math.max(cardMinWidth, 420),
              cardHeight: Math.max(cardHeight, 420),
            }}
            steps={{
              objectStepSelection: objectStepSelection,
              updateObjectStep: updateObjectStep,
              debouncedObjectStepSelection: debouncedObjectStepSelection,
            }}
            overrides={{
              experimentStepOverrideEnabled: experimentStepOverrideEnabled,
              setExperimentStepOverrideEnabled:
                setExperimentStepOverrideEnabled,
              enableExperimentStepOverride: enableExperimentStepOverride,
              experimentStepOverrides: experimentStepOverrides,
              updateExperimentStepOverride: updateExperimentStepOverride,
              debouncedExperimentStepOverrides:
                debouncedExperimentStepOverrides,
            }}
            filter={{
              onlyArtifactId: fullscreenArtifactId,
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
