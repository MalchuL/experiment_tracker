"use client";

import { useMemo, type Dispatch, type SetStateAction } from "react";
import { parseISO } from "date-fns";
import type { Experiment } from "@/domain/experiments/types";
import type { LoggedObjectGroups } from "../types";
import { LoggedObjectCard } from "./artifacts/logged-object-card";

export interface LoggedObjectsSectionProps {
  projectId: string;
  objectGroups: LoggedObjectGroups;
  visibleExperiments: Experiment[];
  onImagePreview: (payload: { src: string; title: string }) => void;
  showSectionHeader?: boolean;
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
  filter?: {
    hiddenArtifactIds?: Set<string>;
    onlyArtifactId?: string | null;
    artifactType?: string;
    artifactNames?: string[];
  };
}

export function LoggedObjectsSection({
  projectId,
  objectGroups,
  visibleExperiments,
  size,
  steps,
  overrides,
  onImagePreview,
  filter: {
    hiddenArtifactIds = new Set<string>(),
    onlyArtifactId = null,
    artifactType,
    artifactNames,
  } = {},
  showSectionHeader = true,
}: LoggedObjectsSectionProps) {
  const experiments = useMemo(
    () =>
      [...visibleExperiments].sort(
        (a, b) =>
          parseISO(b.createdAt).getTime() - parseISO(a.createdAt).getTime(),
      ),
    [visibleExperiments],
  );
  const typeEntries = useMemo(() => {
    if (!artifactType) return Object.entries(objectGroups);
    const byName = objectGroups[artifactType];
    return byName ? [[artifactType, byName] as const] : [];
  }, [artifactType, objectGroups]);
  if (!typeEntries.length) return null;
  return (
    <div className={showSectionHeader ? "mt-4 space-y-4" : "space-y-4"}>
      {showSectionHeader && (
        <div>
          <h2 className="text-base font-semibold">Logged Objects</h2>
          <p className="text-sm text-muted-foreground">
            Objects are grouped by type and name; each card shows one object per
            selected experiment at the chosen step.
          </p>
        </div>
      )}
      {typeEntries.map(([objectType, byName]) => (
        <div key={objectType} className="space-y-2">
          {showSectionHeader && !artifactType && (
            <h3 className="text-sm font-medium capitalize">
              {objectType.replaceAll("_", " ")}
            </h3>
          )}
          <div
            className="grid gap-3"
            style={{
              gridTemplateColumns: `repeat(auto-fill, ${size.cardMinWidth}px)`,
              justifyContent: "start",
            }}
          >
            {Object.entries(byName).map(([name, group]) => {
              const selectionKey = `${objectType}:${name}`;
              if (artifactNames && !artifactNames.includes(name)) return null;
              if (
                hiddenArtifactIds.has(selectionKey) ||
                (onlyArtifactId && onlyArtifactId !== selectionKey)
              )
                return null;
              return (
                <LoggedObjectCard
                  key={selectionKey}
                  projectId={projectId}
                  object={{ objectType, name, group }}
                  experiments={experiments}
                  size={size}
                  steps={steps}
                  overrides={overrides}
                  onImagePreview={onImagePreview}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
