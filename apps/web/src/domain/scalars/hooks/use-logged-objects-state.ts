import { useCallback, useEffect, useMemo, useState } from "react";
import type { LoggedObjectGroups } from "@/domain/scalars/types";

function buildStepCatalog(objectGroups: LoggedObjectGroups): Record<string, number[]> {
  const catalog: Record<string, number[]> = {};
  Object.entries(objectGroups).forEach(([objectType, byName]) => {
    Object.entries(byName).forEach(([name, group]) => {
      catalog[`${objectType}:${name}`] = group.steps;
    });
  });
  return catalog;
}

function buildOverrideStepCatalog(objectGroups: LoggedObjectGroups): Record<string, number[]> {
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

export function useLoggedObjectsState(objectGroups: LoggedObjectGroups = {}) {
  const [objectStepSelection, setObjectStepSelection] = useState<Record<string, number>>({});
  const [debouncedObjectStepSelection, setDebouncedObjectStepSelection] = useState<Record<string, number>>({});
  const [followLatestStep, setFollowLatestStep] = useState<Record<string, boolean>>({});
  const [followLatestOverrideStep, setFollowLatestOverrideStep] = useState<Record<string, boolean>>({});
  const [experimentStepOverrideEnabled, setExperimentStepOverrideEnabled] = useState<Record<string, boolean>>({});
  const [experimentStepOverrides, setExperimentStepOverrides] = useState<Record<string, number>>({});
  const [debouncedExperimentStepOverrides, setDebouncedExperimentStepOverrides] = useState<Record<string, number>>(
    {}
  );

  const stepCatalog = useMemo(() => buildStepCatalog(objectGroups), [objectGroups]);
  const stepCatalogSignature = useMemo(() => JSON.stringify(stepCatalog), [stepCatalog]);
  const overrideStepCatalog = useMemo(() => buildOverrideStepCatalog(objectGroups), [objectGroups]);
  const overrideStepCatalogSignature = useMemo(
    () => JSON.stringify(overrideStepCatalog),
    [overrideStepCatalog]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedObjectStepSelection(objectStepSelection);
      setDebouncedExperimentStepOverrides(experimentStepOverrides);
    }, 500);
    return () => window.clearTimeout(timer);
  }, [objectStepSelection, experimentStepOverrides]);

  /** When new steps arrive, keep pinned-to-end sliders on the latest step. */
  useEffect(() => {
    const catalog = JSON.parse(stepCatalogSignature) as Record<string, number[]>;
    setObjectStepSelection((prev) => {
      let next: Record<string, number> | null = null;
      const debouncedUpdates: Record<string, number> = {};

      Object.entries(catalog).forEach(([key, steps]) => {
        if (steps.length === 0) return;
        if (followLatestStep[key] === false) return;

        const latest = steps[steps.length - 1];
        const current = (next ?? prev)[key];
        if (current === latest) return;

        if (!next) next = { ...prev };
        next[key] = latest;
        debouncedUpdates[key] = latest;
      });

      if (Object.keys(debouncedUpdates).length > 0) {
        setDebouncedObjectStepSelection((debouncedPrev) => ({
          ...debouncedPrev,
          ...debouncedUpdates,
        }));
      }

      return next ?? prev;
    });
  }, [followLatestStep, stepCatalogSignature]);

  /** When new per-experiment steps arrive, keep pinned override sliders on the latest step. */
  useEffect(() => {
    const catalog = JSON.parse(overrideStepCatalogSignature) as Record<string, number[]>;
    setExperimentStepOverrides((prev) => {
      let next: Record<string, number> | null = null;
      const debouncedUpdates: Record<string, number> = {};

      Object.entries(catalog).forEach(([key, steps]) => {
        if (steps.length === 0) return;
        if (followLatestOverrideStep[key] !== true) return;
        if (!experimentStepOverrideEnabled[key]) return;

        const latest = steps[steps.length - 1];
        const current = (next ?? prev)[key];
        if (current === latest) return;

        if (!next) next = { ...prev };
        next[key] = latest;
        debouncedUpdates[key] = latest;
      });

      if (Object.keys(debouncedUpdates).length > 0) {
        setDebouncedExperimentStepOverrides((debouncedPrev) => ({
          ...debouncedPrev,
          ...debouncedUpdates,
        }));
      }

      return next ?? prev;
    });
  }, [experimentStepOverrideEnabled, followLatestOverrideStep, overrideStepCatalogSignature]);

  const updateObjectStep = useCallback(
    (selectionKey: string, step: number, followLatest: boolean) => {
      setFollowLatestStep((prev) => ({
        ...prev,
        [selectionKey]: followLatest,
      }));
      setObjectStepSelection((prev) => ({
        ...prev,
        [selectionKey]: step,
      }));
    },
    []
  );

  const enableExperimentStepOverride = useCallback(
    (overrideKey: string, step: number, followLatest = false) => {
      setExperimentStepOverrideEnabled((prev) => ({
        ...prev,
        [overrideKey]: true,
      }));
      setExperimentStepOverrides((prev) => ({
        ...prev,
        [overrideKey]: step,
      }));
      setFollowLatestOverrideStep((prev) => ({
        ...prev,
        [overrideKey]: followLatest,
      }));
    },
    []
  );

  const updateExperimentStepOverride = useCallback(
    (overrideKey: string, step: number, followLatest: boolean) => {
      setFollowLatestOverrideStep((prev) => ({
        ...prev,
        [overrideKey]: followLatest,
      }));
      setExperimentStepOverrides((prev) => ({
        ...prev,
        [overrideKey]: step,
      }));
    },
    []
  );

  return {
    objectStepSelection,
    setObjectStepSelection,
    updateObjectStep,
    debouncedObjectStepSelection,
    experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled,
    enableExperimentStepOverride,
    experimentStepOverrides,
    setExperimentStepOverrides,
    updateExperimentStepOverride,
    debouncedExperimentStepOverrides,
    stepCatalog,
  };
}
