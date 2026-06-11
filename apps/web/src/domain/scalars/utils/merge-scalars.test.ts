import { describe, expect, it } from "vitest";
import type { ScalarsPointsResult } from "@/domain/scalars/types";
import { mergeScalarsPage } from "./merge-scalars";

function page(data: ScalarsPointsResult["data"]): ScalarsPointsResult {
  return {
    data,
    hasNext: false,
    size: data.length,
    total: data.length,
  };
}

describe("mergeScalarsPage", () => {
  it("replaces values for duplicate steps while merging incoming points", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [1, 2], y: [0.4, 0.3] } },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [2, 3], y: [0.25, 0.2] } },
        },
      ],
      { maxPoints: 10 }
    );

    expect(result.data[0]?.scalars.loss).toEqual({
      x: [1, 2, 3],
      y: [0.4, 0.25, 0.2],
    });
  });

  it("samples merged points to maxPoints and always keeps the latest step", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [1, 2, 3, 4], y: [10, 20, 30, 40] } },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [5, 6, 7, 8], y: [50, 60, 70, 80] } },
        },
      ],
      { maxPoints: 4 }
    );

    const series = result.data[0]?.scalars.loss;
    expect(series?.x).toHaveLength(4);
    expect(series?.y).toHaveLength(4);
    expect(series?.x.at(-1)).toBe(8);
    expect(series?.y.at(-1)).toBe(80);
  });

  it("keeps historical coverage when a dense incremental slice arrives", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: {
            loss: {
              x: [1, 101, 201, 301, 401, 501, 601, 701, 801, 901],
              y: [1, 101, 201, 301, 401, 501, 601, 701, 801, 901],
            },
          },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: {
            loss: {
              x: [902, 903, 904, 905, 906, 907, 908, 909, 910, 911],
              y: [902, 903, 904, 905, 906, 907, 908, 909, 910, 911],
            },
          },
        },
      ],
      { maxPoints: 10 }
    );

    const steps = result.data[0]?.scalars.loss.x ?? [];
    expect(steps).toHaveLength(10);
    expect(steps.at(-1)).toBe(911);
    expect(steps.filter((step) => step < 902).length).toBeGreaterThanOrEqual(8);
  });

  it("keeps only the latest point when maxPoints is one", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [1, 2], y: [10, 20] } },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: { loss: { x: [3], y: [30] } },
        },
      ],
      { maxPoints: 1 }
    );

    expect(result.data[0]?.scalars.loss).toEqual({ x: [3], y: [30] });
  });

  it("merges and preserves non-finite wire values alongside finite points", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: {
            rng: { x: [1, 2, 4], y: [0.5, "nan", 0.25] },
          },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: {
            rng: { x: [3, 5], y: ["inf", 0.1] },
          },
        },
      ],
      { maxPoints: 10 }
    );

    expect(result.data[0]?.scalars.rng).toEqual({
      x: [1, 2, 3, 4, 5],
      y: [0.5, "nan", "inf", 0.25, 0.1],
    });
  });

  it("merges slash-prefixed metric names independently by full name key", () => {
    const result = mergeScalarsPage(
      page([
        {
          experiment_id: "exp-1",
          scalars: {
            "train/loss": { x: [1], y: [0.5] },
            "val/loss": { x: [1], y: [0.9] },
          },
        },
      ]),
      [
        {
          experiment_id: "exp-1",
          scalars: {
            "train/loss": { x: [2], y: [0.4] },
            "val/loss": { x: [2], y: [0.8] },
          },
        },
      ],
      { maxPoints: 10 }
    );

    expect(result.data[0]?.scalars["train/loss"]).toEqual({
      x: [1, 2],
      y: [0.5, 0.4],
    });
    expect(result.data[0]?.scalars["val/loss"]).toEqual({
      x: [1, 2],
      y: [0.9, 0.8],
    });
  });

  it("samples appended missing experiments too", () => {
    const result = mergeScalarsPage(
      page([]),
      [
        {
          experiment_id: "exp-2",
          scalars: { acc: { x: [1, 2, 3, 4], y: [0.1, 0.2, 0.3, 0.4] } },
        },
      ],
      { appendMissing: true, maxPoints: 2 }
    );

    expect(result.data[0]?.scalars.acc.x).toHaveLength(2);
    expect(result.data[0]?.scalars.acc.x.at(-1)).toBe(4);
    expect(result.data[0]?.scalars.acc.y.at(-1)).toBe(0.4);
  });
});
