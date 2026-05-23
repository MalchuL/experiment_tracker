import { describe, expect, it } from "vitest";
import type {
  ArtifactsInfoSummaryResult,
  LoggedArtifactSummaryEntry,
  LoggedObjectType,
} from "@/domain/logged-objects/types";
import { mergeArtifactsInfoPage } from "./merge-artifacts-info";

function summaryEntry(
  overrides: Partial<LoggedArtifactSummaryEntry> & Pick<LoggedArtifactSummaryEntry, "name" | "steps">
): LoggedArtifactSummaryEntry {
  return {
    artifact_type: "image",
    last_modified: "2026-05-20T10:00:00.000Z",
    ...overrides,
  };
}

function page(data: ArtifactsInfoSummaryResult["data"]): ArtifactsInfoSummaryResult {
  return {
    data,
    hasNext: false,
    size: data.length,
    total: data.length,
  };
}

describe("mergeArtifactsInfoPage", () => {
  it("unions steps for an existing experiment, name, and type", () => {
    const result = mergeArtifactsInfoPage(
      page([
        {
          experiment_id: "exp-1",
          artifacts_info: [summaryEntry({ name: "sample", steps: [1] })],
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          artifacts_info: [summaryEntry({ name: "sample", steps: [2] })],
        },
      ]
    );

    expect(result.data[0]?.artifacts_info[0]?.steps).toEqual([1, 2]);
  });

  it("keeps the newest last_modified for matching summary entries", () => {
    const result = mergeArtifactsInfoPage(
      page([
        {
          experiment_id: "exp-1",
          artifacts_info: [
            summaryEntry({
              name: "sample",
              steps: [1],
              last_modified: "2026-05-20T10:00:00.000Z",
            }),
          ],
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          artifacts_info: [
            summaryEntry({
              name: "sample",
              steps: [1, 2],
              last_modified: "2026-05-20T10:01:00.000Z",
            }),
          ],
        },
      ]
    );

    expect(result.data[0]?.artifacts_info[0]).toMatchObject({
      steps: [1, 2],
      last_modified: "2026-05-20T10:01:00.000Z",
    });
  });

  it("adds missing experiments only when appendMissing is enabled", () => {
    const current = page([
      {
        experiment_id: "exp-1",
        artifacts_info: [summaryEntry({ name: "sample", steps: [1] })],
      },
    ]);
    const incoming = [
      {
        experiment_id: "exp-2",
        artifacts_info: [summaryEntry({ name: "sample", steps: [3] })],
      },
    ];

    expect(mergeArtifactsInfoPage(current, incoming).data.map((item) => item.experiment_id)).toEqual([
      "exp-1",
    ]);
    expect(
      mergeArtifactsInfoPage(current, incoming, { appendMissing: true }).data.map(
        (item) => item.experiment_id
      )
    ).toEqual(["exp-2", "exp-1"]);
  });

  it("leaves unrelated experiments unchanged and sorts summary entries", () => {
    const textType: LoggedObjectType = "text";
    const result = mergeArtifactsInfoPage(
      page([
        {
          experiment_id: "exp-1",
          artifacts_info: [
            summaryEntry({ artifact_type: textType, name: "zeta", steps: [2] }),
            summaryEntry({ name: "image", steps: [5] }),
          ],
        },
        {
          experiment_id: "exp-2",
          artifacts_info: [summaryEntry({ name: "other", steps: [1] })],
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          artifacts_info: [
            summaryEntry({ name: "image", steps: [3] }),
            summaryEntry({ artifact_type: textType, name: "alpha", steps: [1] }),
          ],
        },
      ]
    );

    expect(result.data[1]).toEqual({
      experiment_id: "exp-2",
      artifacts_info: [summaryEntry({ name: "other", steps: [1] })],
    });
    expect(
      result.data[0]?.artifacts_info.map((item) => `${item.artifact_type}:${item.name}:${item.steps.join(",")}`)
    ).toEqual(["image:image:3,5", "text:alpha:1", "text:zeta:2"]);
  });
});
