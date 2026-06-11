import { describe, expect, it } from "vitest";
import {
  computeIncrementalStartTime,
  hasCompleteIncrementalBaseline,
  pickIncrementalChanges,
} from "./incremental-refresh";

describe("pickIncrementalChanges", () => {
  it("includes experiments missing from cache", () => {
    const changed = pickIncrementalChanges({
      lastLogged: [{ experiment_id: "exp-2", last_modified: "2026-05-20T10:00:00.000Z" }],
      cachedExperimentIds: new Set(["exp-1"]),
      previousModifiedByExperiment: new Map(),
    });

    expect(changed).toHaveLength(1);
    expect(changed[0]?.missingFromCache).toBe(true);
  });

  it("skips first poll when no previous timestamp exists", () => {
    const changed = pickIncrementalChanges({
      lastLogged: [{ experiment_id: "exp-1", last_modified: "2026-05-20T10:00:00.000Z" }],
      cachedExperimentIds: new Set(["exp-1"]),
      previousModifiedByExperiment: new Map(),
    });

    expect(changed).toHaveLength(0);
  });

  it("detects timestamp advances for cached experiments", () => {
    const changed = pickIncrementalChanges({
      lastLogged: [{ experiment_id: "exp-1", last_modified: "2026-05-20T10:01:00.000Z" }],
      cachedExperimentIds: new Set(["exp-1"]),
      previousModifiedByExperiment: new Map([
        ["exp-1", "2026-05-20T10:00:00.000Z"],
      ]),
    });

    expect(changed).toHaveLength(1);
    expect(changed[0]?.previousModified).toBe("2026-05-20T10:00:00.000Z");
  });
});

describe("hasCompleteIncrementalBaseline", () => {
  it("returns false until every watched experiment has a baseline timestamp", () => {
    expect(
      hasCompleteIncrementalBaseline(
        [{ experiment_id: "exp-1", last_modified: "2026-05-20T10:00:00.000Z" }],
        new Map()
      )
    ).toBe(false);
    expect(
      hasCompleteIncrementalBaseline(
        [{ experiment_id: "exp-1", last_modified: "2026-05-20T10:00:00.000Z" }],
        new Map([["exp-1", "2026-05-20T10:00:00.000Z"]])
      )
    ).toBe(true);
  });
});

describe("computeIncrementalStartTime", () => {
  it("returns undefined when any changed row is missing from cache", () => {
    expect(
      computeIncrementalStartTime([
        {
          item: { experiment_id: "exp-1", last_modified: "2026-05-20T10:01:00.000Z" },
          previousModified: "2026-05-20T10:00:00.000Z",
          missingFromCache: true,
        },
      ])
    ).toBeUndefined();
  });

  it("uses earliest previous timestamp for incremental fetch", () => {
    expect(
      computeIncrementalStartTime([
        {
          item: { experiment_id: "exp-1", last_modified: "2026-05-20T10:02:00.000Z" },
          previousModified: "2026-05-20T10:01:00.000Z",
          missingFromCache: false,
        },
        {
          item: { experiment_id: "exp-2", last_modified: "2026-05-20T10:03:00.000Z" },
          previousModified: "2026-05-20T10:00:00.000Z",
          missingFromCache: false,
        },
      ])
    ).toBe("2026-05-20T10:00:00.000Z");
  });
});
