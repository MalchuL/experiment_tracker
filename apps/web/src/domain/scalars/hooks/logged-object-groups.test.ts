import { describe, expect, it } from "vitest";
import type { Experiment } from "@/domain/experiments/types";
import type { ExperimentArtifactsSummary } from "@/domain/logged-objects/types";
import { buildLoggedObjectGroups } from "./build-logged-object-groups";

const visibleExperiments = [
  { id: "exp-1", name: "Run 1" },
  { id: "exp-2", name: "Run 2" },
] as Experiment[];

describe("buildLoggedObjectGroups", () => {
  it("groups by artifact type and preserves slash-prefixed names", () => {
    const projectArtifacts: ExperimentArtifactsSummary[] = [
      {
        experiment_id: "exp-1",
        artifacts_info: [
          {
            name: "train/sample",
            artifact_type: "image",
            steps: [1, 2],
            last_modified: "2026-05-20T10:00:00.000Z",
          },
        ],
      },
    ];

    const groups = buildLoggedObjectGroups(projectArtifacts, visibleExperiments);
    expect(Object.keys(groups.image ?? {})).toEqual(["train/sample"]);
    expect(groups.image?.["train/sample"].steps).toEqual([1, 2]);
  });

  it("excludes deselected experiments from byExperiment maps", () => {
    const projectArtifacts: ExperimentArtifactsSummary[] = [
      {
        experiment_id: "exp-1",
        artifacts_info: [
          {
            name: "train/sample",
            artifact_type: "image",
            steps: [1],
            last_modified: "2026-05-20T10:00:00.000Z",
          },
        ],
      },
      {
        experiment_id: "exp-2",
        artifacts_info: [
          {
            name: "train/sample",
            artifact_type: "image",
            steps: [3],
            last_modified: "2026-05-20T10:01:00.000Z",
          },
        ],
      },
    ];

    const groups = buildLoggedObjectGroups(projectArtifacts, [visibleExperiments[0]!]);
    expect(groups.image?.["train/sample"].steps).toEqual([1]);
    expect(groups.image?.["train/sample"].byExperiment["exp-2"]).toBeUndefined();
  });
});
