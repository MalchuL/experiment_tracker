import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { experimentArtifactsService } from "./service";
import type { NamedArtifactPreview, NamedExperimentArtifact } from "./types";

export function useExperimentFinalArtifacts(experimentId?: string, names?: string[]) {
  const stableNames = useMemo(() => [...(names ?? [])].sort(), [names]);
  const { data, isLoading, isFetching, refetch } = useQuery<NamedExperimentArtifact[]>({
    queryKey: experimentId
      ? [QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(experimentId), { names: stableNames }]
      : [],
    queryFn: () => experimentArtifactsService.listByExperiment(experimentId!, stableNames),
    enabled: !!experimentId,
  });

  return {
    artifacts: data ?? [],
    isLoading,
    isFetching,
    refetch,
  };
}

export function useCompareFinalArtifacts(experimentIds: string[]) {
  const stableExperimentIds = useMemo(
    () => [...new Set(experimentIds.filter(Boolean))].sort(),
    [experimentIds]
  );

  const queryResults = useQueries({
    queries: stableExperimentIds.map((experimentId) => ({
      queryKey: [QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(experimentId)],
      queryFn: () => experimentArtifactsService.listByExperiment(experimentId),
      enabled: !!experimentId,
    })),
  });

  const isLoading = queryResults.some((result) => result.isLoading);
  const isFetching = queryResults.some((result) => result.isFetching);
  const artifactsByExperiment = stableExperimentIds.reduce<
    Record<string, NamedExperimentArtifact[]>
  >((acc, experimentId, index) => {
    acc[experimentId] = queryResults[index]?.data ?? [];
    return acc;
  }, {});

  return {
    artifactsByExperiment,
    isLoading,
    isFetching,
  };
}

export function useFinalArtifactPreviews(
  artifacts: NamedExperimentArtifact[],
  maxBytes = 2 * 1024 * 1024
) {
  const stableArtifacts = useMemo(
    () =>
      [...artifacts].sort((a, b) => {
        if (a.name !== b.name) return a.name.localeCompare(b.name);
        return a.filepath.localeCompare(b.filepath);
      }),
    [artifacts]
  );

  const previewQueries = useQueries({
    queries: stableArtifacts.map((artifact) => ({
      queryKey: [
        QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(artifact.experimentId),
        "preview",
        artifact.name,
        artifact.filepath,
        maxBytes,
      ],
      queryFn: () =>
        experimentArtifactsService.previewNamedArtifact(
          artifact.experimentId,
          artifact.name,
          artifact.filepath,
          maxBytes
        ),
      enabled: !!artifact.experimentId,
    })),
  });

  const previewsByArtifactId = stableArtifacts.reduce<
    Record<string, NamedArtifactPreview | undefined>
  >((acc, artifact, index) => {
    acc[artifact.id] = previewQueries[index]?.data;
    return acc;
  }, {});

  const isLoading = previewQueries.some((query) => query.isLoading);
  const isFetching = previewQueries.some((query) => query.isFetching);

  return { previewsByArtifactId, isLoading, isFetching };
}

