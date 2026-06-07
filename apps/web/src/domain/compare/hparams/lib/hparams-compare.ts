import { jsonPath } from "@/domain/experiments/lib/hparams-json";
import type { HparamsDocument, JsonValue } from "@/domain/experiments/types";

export interface HparamsLeaf {
  path: (string | number)[];
  pathKey: string;
  value: JsonValue;
}

export type HparamsComparisonMode = "baseline" | "previous";

export interface HparamsCompareRow {
  path: (string | number)[];
  pathKey: string;
  values: (JsonValue | undefined)[];
}

export function flattenHparams(value: HparamsDocument): HparamsLeaf[] {
  const leaves: HparamsLeaf[] = [];
  const visit = (item: JsonValue, path: (string | number)[]) => {
    if (Array.isArray(item)) {
      if (item.length === 0) leaves.push({ path, pathKey: jsonPath(path), value: item });
      item.forEach((child, index) => visit(child, [...path, index]));
      return;
    }
    if (item !== null && typeof item === "object") {
      const entries = Object.entries(item);
      if (entries.length === 0) leaves.push({ path, pathKey: jsonPath(path), value: item });
      entries.forEach(([key, child]) => visit(child, [...path, key]));
      return;
    }
    leaves.push({ path, pathKey: jsonPath(path), value: item });
  };
  Object.entries(value).forEach(([key, child]) => visit(child, [key]));
  return leaves.sort((a, b) => a.pathKey.localeCompare(b.pathKey));
}

export function buildHparamsCompareRows(
  experiments: Array<{ hparams: HparamsDocument | null }>
): HparamsCompareRow[] {
  const maps = experiments.map(
    (experiment) =>
      new Map(
        experiment.hparams
          ? flattenHparams(experiment.hparams).map((leaf) => [leaf.pathKey, leaf] as const)
          : []
      )
  );
  const keys = Array.from(new Set(maps.flatMap((map) => Array.from(map.keys())))).sort();
  return keys.map((pathKey) => {
    const leaves = maps.map((map) => map.get(pathKey));
    return {
      pathKey,
      path: leaves.find(Boolean)?.path ?? [],
      values: leaves.map((leaf) => leaf?.value),
    };
  });
}
