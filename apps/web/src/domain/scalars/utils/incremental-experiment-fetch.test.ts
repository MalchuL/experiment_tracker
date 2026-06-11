import { describe, expect, it } from "vitest";
import { findMissingExperimentIds } from "./incremental-experiment-fetch";

describe("findMissingExperimentIds", () => {
  it("returns selected ids not yet requested, fetched, or in-flight", () => {
    const missing = findMissingExperimentIds({
      selectedExperimentIds: new Set(["exp-1", "exp-2", "exp-3"]),
      requestedExperimentIds: ["exp-1"],
      fetchedExperimentIds: ["exp-2"],
      incrementalInFlightIds: new Set(["exp-3"]),
    });

    expect(missing).toEqual([]);
  });

  it("includes only ids that still need incremental fetch", () => {
    const missing = findMissingExperimentIds({
      selectedExperimentIds: new Set(["exp-1", "exp-2", "exp-4"]),
      requestedExperimentIds: ["exp-1"],
      fetchedExperimentIds: ["exp-2"],
      incrementalInFlightIds: new Set(),
    });

    expect(missing).toEqual(["exp-4"]);
  });
});
