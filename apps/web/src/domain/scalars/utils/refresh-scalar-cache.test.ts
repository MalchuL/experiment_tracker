import { describe, expect, it, vi } from "vitest";
import { refreshScalarCache, type ScalarCache } from "./refresh-scalar-cache";

const watermark = (time: number) => `2026-01-01T00:00:${String(time).padStart(2, "0")}.000Z`;
const rows = (steps: number[]) => [{ experiment_id: "exp", scalars: { loss: { x: steps, y: steps } } }];
const cached: ScalarCache = { data: rows([0, 1]), watermarks: { exp: watermark(1) } };

describe("scalar cache transaction", () => {
  it("catches up from the cached watermark after navigation, preserving history", async () => {
    const fetchPoints = vi.fn().mockResolvedValue(rows([2, 3, 4]));
    const next = await refreshScalarCache(cached, [{ experiment_id: "exp", last_modified: watermark(4) }], fetchPoints, 100);
    expect(fetchPoints).toHaveBeenCalledWith(["exp"], watermark(1));
    expect(next.data[0].scalars.loss.x).toEqual([0, 1, 2, 3, 4]);
    expect(next.watermarks.exp).toBe(watermark(4));
  });

  it("does not commit a failed or incomplete fetch, and retries the same interval", async () => {
    const fetchPoints = vi.fn().mockRejectedValueOnce(new Error("second page failed")).mockResolvedValue(rows([2]));
    const latest = [{ experiment_id: "exp", last_modified: watermark(2) }];
    await expect(refreshScalarCache(cached, latest, fetchPoints, 100)).rejects.toThrow();
    expect(cached.watermarks.exp).toBe(watermark(1));
    await refreshScalarCache(cached, latest, fetchPoints, 100);
    expect(fetchPoints.mock.calls).toEqual([[['exp'], watermark(1)], [['exp'], watermark(1)]]);
  });

  it("uses a full baseline after eviction and does not pollute another scalar cache", async () => {
    const fetchPoints = vi.fn().mockResolvedValue(rows([0, 1, 2]));
    await refreshScalarCache(undefined, [{ experiment_id: "exp", last_modified: watermark(2) }], fetchPoints, 2);
    expect(fetchPoints).toHaveBeenCalledWith(undefined, undefined);
    expect(cached.data[0].scalars.loss.x).toEqual([0, 1]);
  });

  it("keeps the exact cached object when nothing changed", async () => {
    const fetchPoints = vi.fn();
    expect(await refreshScalarCache(cached, [{ experiment_id: "exp", last_modified: watermark(1) }], fetchPoints, 100)).toBe(cached);
    expect(fetchPoints).not.toHaveBeenCalled();
  });
});
