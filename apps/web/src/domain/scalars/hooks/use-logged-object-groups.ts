import { useMemo } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentArtifactsSummary } from "@/domain/logged-objects/types";
import type { LoggedObjectGroups } from "@/domain/scalars/types";

export function useLoggedObjectGroups(
  projectArtifacts: ExperimentArtifactsSummary[],
  visibleExperiments: Experiment[]
) {
  return useMemo(() => {
    const visibleIds = new Set(visibleExperiments.map((experiment) => experiment.id));
    const grouped: LoggedObjectGroups = {};

    projectArtifacts.forEach((experimentArtifacts) => {
      if (!visibleIds.has(experimentArtifacts.experiment_id)) return;
      experimentArtifacts.artifacts_info.forEach((obj) => {
        const typeGroup = grouped[obj.artifact_type] || {};
        const nameGroup = typeGroup[obj.name] || { steps: [], byExperiment: {} };
        const byStep = nameGroup.byExperiment[experimentArtifacts.experiment_id] || {};
        obj.steps.forEach((step) => {
          byStep[step] = {
            lastModified: obj.last_modified,
          };
          if (!nameGroup.steps.includes(step)) {
            nameGroup.steps.push(step);
          }
        });
        nameGroup.byExperiment[experimentArtifacts.experiment_id] = byStep;
        typeGroup[obj.name] = nameGroup;
        grouped[obj.artifact_type] = typeGroup;
      });
    });

    Object.values(grouped).forEach((nameMap) => {
      Object.values(nameMap).forEach((nameGroup) => {
        nameGroup.steps.sort((a, b) => a - b);
      });
    });

    return grouped;
  }, [projectArtifacts, visibleExperiments]);
}
