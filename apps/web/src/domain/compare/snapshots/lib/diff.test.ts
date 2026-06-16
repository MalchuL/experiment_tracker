import { describe, expect, it } from "vitest";
import { computeSideBySideDiff } from "./diff";

describe("computeSideBySideDiff", () => {
  it("aligns inserted lines without shifting unchanged context", () => {
    const oldContent = "line1\nline2";
    const newContent = "line1\nnew line\nline2";

    expect(computeSideBySideDiff(oldContent, newContent)).toEqual([
      {
        type: "same",
        leftLineNumber: 1,
        rightLineNumber: 1,
        leftContent: "line1",
        rightContent: "line1",
      },
      {
        type: "added",
        rightLineNumber: 2,
        rightContent: "new line",
      },
      {
        type: "same",
        leftLineNumber: 2,
        rightLineNumber: 3,
        leftContent: "line2",
        rightContent: "line2",
      },
    ]);
  });

  it("pairs adjacent remove/add rows as changed lines", () => {
    const oldContent = "alpha\nbeta";
    const newContent = "alpha\nbeta updated";

    expect(computeSideBySideDiff(oldContent, newContent)).toEqual([
      {
        type: "same",
        leftLineNumber: 1,
        rightLineNumber: 1,
        leftContent: "alpha",
        rightContent: "alpha",
      },
      {
        type: "changed",
        leftLineNumber: 2,
        rightLineNumber: 2,
        leftContent: "beta",
        rightContent: "beta updated",
      },
    ]);
  });
});
