import type { LoggedObjectGroups } from "@/domain/scalars/types";

export function buildStepCatalog(objectGroups: LoggedObjectGroups): Record<string, number[]> {
  const catalog: Record<string, number[]> = {};
  Object.entries(objectGroups).forEach(([objectType, byName]) => {
    Object.entries(byName).forEach(([name, group]) => {
      catalog[`${objectType}:${name}`] = group.steps;
    });
  });
  return catalog;
}

export function buildOverrideStepCatalog(objectGroups: LoggedObjectGroups): Record<string, number[]> {
  const catalog: Record<string, number[]> = {};
  Object.entries(objectGroups).forEach(([objectType, byName]) => {
    Object.entries(byName).forEach(([name, group]) => {
      const selectionKey = `${objectType}:${name}`;
      Object.entries(group.byExperiment).forEach(([experimentId, stepMap]) => {
        catalog[`${selectionKey}:${experimentId}`] = Object.keys(stepMap)
          .map((step) => Number(step))
          .filter((step) => Number.isFinite(step))
          .sort((a, b) => a - b);
      });
    });
  });
  return catalog;
}

export function applyFollowLatestObjectSteps(params: {
  catalog: Record<string, number[]>;
  previous: Record<string, number>;
  followLatestStep: Record<string, boolean>;
}): { next: Record<string, number>; debouncedUpdates: Record<string, number> } {
  const next = { ...params.previous };
  const debouncedUpdates: Record<string, number> = {};

  Object.entries(params.catalog).forEach(([key, steps]) => {
    if (steps.length === 0) return;
    if (params.followLatestStep[key] === false) return;

    const latest = steps[steps.length - 1]!;
    if (next[key] === latest) return;

    next[key] = latest;
    debouncedUpdates[key] = latest;
  });

  return { next, debouncedUpdates };
}

export function applyFollowLatestOverrideSteps(params: {
  catalog: Record<string, number[]>;
  previous: Record<string, number>;
  followLatestOverrideStep: Record<string, boolean>;
  experimentStepOverrideEnabled: Record<string, boolean>;
}): { next: Record<string, number>; debouncedUpdates: Record<string, number> } {
  const next = { ...params.previous };
  const debouncedUpdates: Record<string, number> = {};

  Object.entries(params.catalog).forEach(([key, steps]) => {
    if (steps.length === 0) return;
    if (params.followLatestOverrideStep[key] !== true) return;
    if (!params.experimentStepOverrideEnabled[key]) return;

    const latest = steps[steps.length - 1]!;
    if (next[key] === latest) return;

    next[key] = latest;
    debouncedUpdates[key] = latest;
  });

  return { next, debouncedUpdates };
}
