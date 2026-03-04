import { useMemo } from "react";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentArtifactsInfo } from "@/domain/logged-objects/types";
import type { LoggedObjectGroups } from "@/domain/scalars/types";

export function useLoggedObjectGroups(
  projectArtifacts: ExperimentArtifactsInfo[],
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
        byStep[obj.step] = {
          path: obj.path,
          metadata: obj.metadata || {},
          timestamp: obj.timestamp,
        };
        nameGroup.byExperiment[experimentArtifacts.experiment_id] = byStep;
        if (!nameGroup.steps.includes(obj.step)) {
          nameGroup.steps.push(obj.step);
        }
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
