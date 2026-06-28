"use client";

import { useCallback, useState } from "react";

export function useOrderedExperimentSelection() {
  const [selectionMode, setSelectionModeState] = useState(false);
  const [orderedIds, setOrderedIds] = useState<string[]>([]);

  const setSelectionMode = useCallback((on: boolean) => {
    setSelectionModeState(on);
    if (!on) {
      setOrderedIds([]);
    }
  }, []);

  const toggleExperiment = useCallback((id: string) => {
    setOrderedIds((prev) => {
      const index = prev.indexOf(id);
      if (index === -1) {
        return [...prev, id];
      }
      return prev.filter((existingId) => existingId !== id);
    });
  }, []);

  const selectExperiments = useCallback((ids: string[]) => {
    setOrderedIds(ids);
  }, []);

  const clearSelection = useCallback(() => {
    setOrderedIds([]);
  }, []);

  const getOrderNumber = useCallback(
    (id: string): number | null => {
      const index = orderedIds.indexOf(id);
      return index === -1 ? null : index + 1;
    },
    [orderedIds]
  );

  return {
    selectionMode,
    setSelectionMode,
    orderedIds,
    toggleExperiment,
    selectExperiments,
    clearSelection,
    getOrderNumber,
    selectedCount: orderedIds.length,
  };
}
