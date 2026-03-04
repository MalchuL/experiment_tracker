import { useEffect, useState } from "react";

export function useLoggedObjectsState() {
  const [objectStepSelection, setObjectStepSelection] = useState<Record<string, number>>({});
  const [debouncedObjectStepSelection, setDebouncedObjectStepSelection] = useState<Record<string, number>>({});
  const [experimentStepOverrideEnabled, setExperimentStepOverrideEnabled] = useState<Record<string, boolean>>({});
  const [experimentStepOverrides, setExperimentStepOverrides] = useState<Record<string, number>>({});
  const [debouncedExperimentStepOverrides, setDebouncedExperimentStepOverrides] = useState<Record<string, number>>(
    {}
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedObjectStepSelection(objectStepSelection);
      setDebouncedExperimentStepOverrides(experimentStepOverrides);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [objectStepSelection, experimentStepOverrides]);

  return {
    objectStepSelection,
    setObjectStepSelection,
    debouncedObjectStepSelection,
    experimentStepOverrideEnabled,
    setExperimentStepOverrideEnabled,
    experimentStepOverrides,
    setExperimentStepOverrides,
    debouncedExperimentStepOverrides,
  };
}
