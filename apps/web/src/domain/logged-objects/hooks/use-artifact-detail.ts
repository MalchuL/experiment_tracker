import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { loggedObjectsService } from "@/domain/logged-objects/services";
import type { LoggedArtifactEntry } from "@/domain/logged-objects/types";

interface UseArtifactDetailParams {
  projectId?: string;
  experimentId?: string;
  objectType?: string;
  name?: string;
  step?: number | null;
  enabled?: boolean;
}

/**
 * Lazily load the full artifact_info row for one selected slider step.
 *
 * The summary endpoint gives the UI enough data to draw sliders. This hook is used only for visible
 * artifact cards so path/timestamp metadata can cache-bust the download URL without preloading every
 * artifact_info row.
 */
export function useArtifactDetail({
  projectId,
  experimentId,
  objectType,
  name,
  step,
  enabled = true,
}: UseArtifactDetailParams) {
  const query = useQuery({
    queryKey:
      projectId && experimentId && name && step !== null && step !== undefined
        ? ["artifact-detail-at-step", projectId, experimentId, objectType, name, step]
        : [],
    queryFn: () =>
      loggedObjectsService.getDetailByProject(projectId!, {
        experimentId: experimentId!,
        objectType,
        name: name!,
        step: step!,
      }),
    enabled:
      !!projectId &&
      !!experimentId &&
      !!name &&
      step !== null &&
      step !== undefined &&
      enabled,
    staleTime: 30_000,
  });

  const artifact = useMemo<LoggedArtifactEntry | undefined>(() => {
    const entries = query.data?.data.flatMap((group) => group.artifacts_info) ?? [];
    return entries.length === 1 ? entries[0] : undefined;
  }, [query.data]);

  return { ...query, artifact };
}
