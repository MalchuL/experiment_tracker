import { useMemo } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentArtifactsSummary } from "@/domain/logged-objects/types";
import { buildLoggedObjectGroups } from "@/domain/scalars/hooks/build-logged-object-groups";

export { buildLoggedObjectGroups } from "@/domain/scalars/hooks/build-logged-object-groups";

export function useLoggedObjectGroups(
  projectArtifacts: ExperimentArtifactsSummary[],
  visibleExperiments: Experiment[]
) {
  return useMemo(
    () => buildLoggedObjectGroups(projectArtifacts, visibleExperiments),
    [projectArtifacts, visibleExperiments]
  );
}
