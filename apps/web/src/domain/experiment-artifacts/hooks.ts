import { useMemo } from "react";
import { useEffect } from "react";
import { useInfiniteQuery, useQueries } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { DEFAULT_PAGE_SIZE } from "@/lib/constants/pagination";
import { experimentArtifactsService } from "./service";
import type { NamedArtifactPreview, NamedExperimentArtifact } from "./types";

export function useExperimentFinalArtifacts(experimentId?: string, names?: string[]) {
  const stableNames = useMemo(() => [...(names ?? [])].sort(), [names]);
  const {
    data,
    isLoading,
    isFetching,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch,
  } = useInfiniteQuery({
    queryKey: experimentId
      ? [QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(experimentId), { names: stableNames, limit: DEFAULT_PAGE_SIZE }]
      : [],
    queryFn: ({ pageParam }) =>
      experimentArtifactsService.listByExperiment(experimentId!, stableNames, {
        limit: DEFAULT_PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if (!lastPage.hasNext) {
        return undefined;
      }
      return allPages.reduce((total, page) => total + page.data.length, 0);
    },
    enabled: !!experimentId,
  });
  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) {
      void fetchNextPage();
    }
  }, [data?.pages.length, fetchNextPage, hasNextPage, isFetchingNextPage]);

  const artifacts = useMemo(
    () => data?.pages.flatMap((page) => page.data) ?? [],
    [data]
  );

  return {
    artifacts,
    isLoading,
    isFetching,
    isFetchingNextPage,
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
      queryFn: async () => {
        const artifacts: NamedExperimentArtifact[] = [];
        let offset = 0;

        while (true) {
          const page = await experimentArtifactsService.listByExperiment(
            experimentId,
            undefined,
            {
              limit: DEFAULT_PAGE_SIZE,
              offset,
            }
          );
          artifacts.push(...page.data);
          if (!page.hasNext) {
            return artifacts;
          }
          offset += page.data.length;
        }
      },
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

export function useFinalArtifactPreviews(artifacts: NamedExperimentArtifact[]) {
  const stableArtifacts = useMemo(
    () =>
      [...artifacts].sort((a, b) => {
        if (a.name !== b.name) return a.name.localeCompare(b.name);
        return a.filepath.localeCompare(b.filepath);
      }),
    [artifacts]
  );

  const previewQueries = useQueries({
    queries: stableArtifacts.map((artifact) => {
      const maxBytes = artifact.mimeType.startsWith("image/")
        ? 10 * 1024 * 1024
        : 2 * 1024 * 1024;
      return {
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
      };
    }),
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

