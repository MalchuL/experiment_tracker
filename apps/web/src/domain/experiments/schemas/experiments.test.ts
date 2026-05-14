import { describe, expect, it } from "vitest";
import { ENTITY_NAME_MAX_LEN } from "@/lib/validation/entity-limits";
import { insertExperimentSchema } from "@/domain/experiments/schemas/experiments";

describe("insertExperimentSchema", () => {
  it("accepts name and description at max length", () => {
    const parsed = insertExperimentSchema.parse({
      projectId: "p",
      name: "n".repeat(ENTITY_NAME_MAX_LEN),
      description: "d".repeat(512),
    });
    expect(parsed.name.length).toBe(ENTITY_NAME_MAX_LEN);
    expect(parsed.description.length).toBe(512);
  });

  it("rejects name over max length", () => {
    expect(() =>
      insertExperimentSchema.parse({
        projectId: "p",
        name: "n".repeat(ENTITY_NAME_MAX_LEN + 1),
        description: "",
      }),
    ).toThrow();
  });
});
