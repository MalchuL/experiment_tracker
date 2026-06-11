"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ExperimentArtifactUploadCard } from "@/domain/experiment-artifacts/components/experiment-artifact-upload-card";
import { FinalArtifactCard } from "@/domain/experiment-artifacts/components/final-artifact-card";
import { Input } from "@/components/ui/input";
import { useExperimentFinalArtifacts } from "@/domain/experiment-artifacts/hooks";
import { useExperiment } from "@/domain/experiments/hooks";

export interface ExperimentArtifactsPanelProps {
  /** Experiment whose final artifacts are listed. */
  experimentId: string;
}

export function ExperimentArtifactsPanel({ experimentId }: ExperimentArtifactsPanelProps) {
  const searchParams = useSearchParams();
  const focusedNameFromQuery = searchParams.get("name") ?? "";
  const [nameFilter, setNameFilter] = useState(focusedNameFromQuery);

  useEffect(() => {
    setNameFilter(focusedNameFromQuery);
  }, [focusedNameFromQuery]);

  const { experiment } = useExperiment(experimentId);
  const {
    artifacts,
    isLoading,
    isFetching,
    isFetchingNextPage,
  } = useExperimentFinalArtifacts(experimentId);

  const filteredArtifacts = useMemo(() => {
    if (!nameFilter.trim()) {
      return artifacts;
    }
    const lowered = nameFilter.trim().toLowerCase();
    return artifacts.filter(
      (artifact) =>
        artifact.name.toLowerCase().includes(lowered) ||
        artifact.filepath.toLowerCase().includes(lowered)
    );
  }, [artifacts, nameFilter]);

  return (
    <div className="space-y-3">
      {experiment ? (
        <p className="text-xs text-muted-foreground">
          Final artifacts for <span className="font-medium text-foreground">{experiment.name}</span>
          . Expand an artifact to load its preview.
        </p>
      ) : null}

      <ExperimentArtifactUploadCard experimentId={experimentId} />

      <div className="space-y-2">
        <Input
          value={nameFilter}
          onChange={(event) => setNameFilter(event.target.value)}
          placeholder="Filter by name or filepath"
          className="h-8 text-sm"
        />
      </div>

      <div className="grid gap-2">
        {isLoading ? (
          <p className="text-xs text-muted-foreground px-1">Loading artifacts...</p>
        ) : filteredArtifacts.length === 0 ? (
          <p className="text-xs text-muted-foreground px-1">
            No final artifacts match this filter.
          </p>
        ) : (
          filteredArtifacts.map((artifact) => (
            <FinalArtifactCard key={artifact.id} artifact={artifact} />
          ))
        )}
      </div>

      {(isFetching || isFetchingNextPage) && !isLoading && (
        <p className="text-xs text-muted-foreground">
          {isFetchingNextPage ? "Loading more artifacts..." : "Refreshing artifacts..."}
        </p>
      )}
    </div>
  );
}
