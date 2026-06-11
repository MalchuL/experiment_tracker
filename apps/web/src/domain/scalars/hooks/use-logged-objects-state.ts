import { useCallback, useEffect, useMemo, useState } from "react";
import type { LoggedObjectGroups } from "@/domain/scalars/types";
import {
  applyFollowLatestObjectSteps,
  applyFollowLatestOverrideSteps,
  buildOverrideStepCatalog,
  buildStepCatalog,
} from "@/domain/scalars/utils/logged-objects-step-state";

export {
  applyFollowLatestObjectSteps,
  applyFollowLatestOverrideSteps,
  buildOverrideStepCatalog,
  buildStepCatalog,
} from "@/domain/scalars/utils/logged-objects-step-state";

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

  useEffect(() => {
    const catalog = JSON.parse(stepCatalogSignature) as Record<string, number[]>;
    setObjectStepSelection((prev) => {
      const { next, debouncedUpdates } = applyFollowLatestObjectSteps({
        catalog,
        previous: prev,
        followLatestStep,
      });

      if (Object.keys(debouncedUpdates).length > 0) {
        setDebouncedObjectStepSelection((debouncedPrev) => ({
          ...debouncedPrev,
          ...debouncedUpdates,
        }));
      }

      return next;
    });
  }, [followLatestStep, stepCatalogSignature]);

  useEffect(() => {
    const catalog = JSON.parse(overrideStepCatalogSignature) as Record<string, number[]>;
    setExperimentStepOverrides((prev) => {
      const { next, debouncedUpdates } = applyFollowLatestOverrideSteps({
        catalog,
        previous: prev,
        followLatestOverrideStep,
        experimentStepOverrideEnabled,
      });

      if (Object.keys(debouncedUpdates).length > 0) {
        setDebouncedExperimentStepOverrides((debouncedPrev) => ({
          ...debouncedPrev,
          ...debouncedUpdates,
        }));
      }

      return next;
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
