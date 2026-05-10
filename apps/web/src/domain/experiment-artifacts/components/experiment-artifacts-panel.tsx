"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FinalArtifactCard } from "@/domain/experiment-artifacts/components/final-artifact-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useExperimentFinalArtifacts,
  useCompareFinalArtifacts,
  useFinalArtifactPreviews,
} from "@/domain/experiment-artifacts/hooks";
import { useExperiment, useExperiments } from "@/domain/experiments/hooks";
import type { NamedExperimentArtifact } from "@/domain/experiment-artifacts/types";

type CompareGroup = Record<string, NamedExperimentArtifact[]>;

function buildNamedArtifactDownloadUrl(
  experimentId: string,
  name: string,
  filepath: string,
  disposition: "attachment" | "inline" = "attachment"
): string {
  const params = new URLSearchParams({
    experiment_id: experimentId,
    name,
    filepath,
    disposition,
  });
  return `/api/experiment-artifacts/named/download?${params.toString()}`;
}

export interface ExperimentArtifactsPanelProps {
  projectId: string;
  /** Primary experiment (final artifacts list, cannot be removed from compare). */
  primaryExperimentId: string;
  /** Default selected experiment ids for compare; URL order. Primary is included. */
  compareExperimentIds: string[];
  /** When true, persist tab in `artTab` query param; otherwise `tab` (legacy). */
  urlTabParam?: boolean;
}

export function ExperimentArtifactsPanel({
  projectId,
  primaryExperimentId,
  compareExperimentIds: initialCompareIds,
  urlTabParam = false,
}: ExperimentArtifactsPanelProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const experimentId = primaryExperimentId;
  const tabParamKey = urlTabParam ? "artTab" : "tab";

  const tabValue = searchParams.get(tabParamKey) === "compare" ? "compare" : "final";

  const focusedNameFromQuery = searchParams.get("name") ?? "";
  const [nameFilter, setNameFilter] = useState(focusedNameFromQuery);

  useEffect(() => {
    setNameFilter(focusedNameFromQuery);
  }, [focusedNameFromQuery]);

  const { experiment } = useExperiment(experimentId);
  const { experiments } = useExperiments(projectId);
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<string[]>(() => {
    return [...new Set([primaryExperimentId, ...initialCompareIds])];
  });

  useEffect(() => {
    setSelectedExperimentIds((prev) => {
      const want = [...new Set([primaryExperimentId, ...initialCompareIds])];
      if (want.length === prev.length && want.every((id, i) => id === prev[i])) {
        return prev;
      }
      return want;
    });
  }, [primaryExperimentId, initialCompareIds]);

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

  const { artifactsByExperiment, isLoading: compareLoading } =
    useCompareFinalArtifacts(selectedExperimentIds);
  const { previewsByArtifactId } = useFinalArtifactPreviews(filteredArtifacts);

  const compareByName = useMemo(() => {
    const grouped: Record<string, CompareGroup> = {};
    for (const [expId, expArtifacts] of Object.entries(artifactsByExperiment)) {
      for (const artifact of expArtifacts) {
        if (!grouped[artifact.name]) {
          grouped[artifact.name] = {};
        }
        if (!grouped[artifact.name][expId]) {
          grouped[artifact.name][expId] = [];
        }
        grouped[artifact.name][expId].push(artifact);
      }
    }
    return Object.entries(grouped)
      .filter(([, byExperiment]) => Object.keys(byExperiment).length > 1)
      .sort(([nameA], [nameB]) => nameA.localeCompare(nameB));
  }, [artifactsByExperiment]);

  const handleTabChange = (value: string) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set(tabParamKey, value === "compare" ? "compare" : "final");
    router.replace(`${pathname}?${next.toString()}`);
  };

  return (
    <div className="space-y-4">
      {experiment ? (
        <p className="text-sm text-muted-foreground">
          Final artifacts for <span className="font-medium text-foreground">{experiment.name}</span>
        </p>
      ) : null}
      <Tabs value={tabValue} onValueChange={handleTabChange} className="space-y-4">
        <TabsList>
          <TabsTrigger value="final">Final Artifacts</TabsTrigger>
          <TabsTrigger value="compare">Compare</TabsTrigger>
        </TabsList>

        <TabsContent value="final" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Filter artifacts</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                value={nameFilter}
                onChange={(event) => setNameFilter(event.target.value)}
                placeholder="Filter by name or filepath"
              />
            </CardContent>
          </Card>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading artifacts...</p>
          ) : filteredArtifacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No final artifacts found for this experiment.
            </p>
          ) : (
            <div className="grid gap-3">
              {filteredArtifacts.map((artifact) => {
                const preview = previewsByArtifactId[artifact.id];
                return (
                  <FinalArtifactCard key={artifact.id} artifact={artifact} preview={preview} />
                );
              })}
            </div>
          )}

          {(isFetching || isFetchingNextPage) && !isLoading && (
            <p className="text-xs text-muted-foreground">
              {isFetchingNextPage ? "Loading more artifacts..." : "Refreshing artifacts..."}
            </p>
          )}
        </TabsContent>

        <TabsContent value="compare" className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Choose experiments to compare</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {experiments.map((candidate) => {
                const checked = selectedExperimentIds.includes(candidate.id);
                return (
                  <label
                    key={candidate.id}
                    className="flex items-center gap-2 text-sm cursor-pointer"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => {
                        const enabled = value === true;
                        setSelectedExperimentIds((prev) => {
                          if (enabled) {
                            return [...new Set([...prev, candidate.id])];
                          }
                          if (candidate.id === experimentId) {
                            return prev;
                          }
                          return prev.filter((id) => id !== candidate.id);
                        });
                      }}
                    />
                    <Label className="cursor-pointer">{candidate.name}</Label>
                  </label>
                );
              })}
            </CardContent>
          </Card>

          {compareLoading ? (
            <p className="text-sm text-muted-foreground">Loading comparison data...</p>
          ) : compareByName.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No shared final artifact names across selected experiments yet.
            </p>
          ) : (
            <div className="space-y-3">
              {compareByName.map(([artifactName, byExperiment]) => (
                <Card key={artifactName}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">{artifactName}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Object.entries(byExperiment).map(([expId, expArtifacts]) => {
                      const expName =
                        experiments.find((candidate) => candidate.id === expId)?.name ?? expId;
                      return (
                        <div key={`${artifactName}:${expId}`} className="space-y-1">
                          <p className="text-sm font-medium">{expName}</p>
                          <ul className="space-y-1">
                            {expArtifacts.map((artifact) => (
                              <li
                                key={artifact.id}
                                className="text-sm text-muted-foreground flex items-center justify-between gap-2"
                              >
                                <span className="truncate">{artifact.filepath}</span>
                                <a
                                  href={buildNamedArtifactDownloadUrl(
                                    artifact.experimentId,
                                    artifact.name,
                                    artifact.filepath,
                                    "attachment"
                                  )}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-primary underline shrink-0"
                                >
                                  Download
                                </a>
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
