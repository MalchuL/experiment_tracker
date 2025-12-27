import { create } from "zustand";

interface ExperimentStore {
  selectedExperimentId: string | null;
  selectedProjectId: string | null;
  isProjectSelectorOpen: boolean;
  setSelectedExperimentId: (id: string | null) => void;
  setSelectedProjectId: (id: string | null) => void;
  openProjectSelector: () => void;
  closeProjectSelector: () => void;
}

export const useExperimentStore = create<ExperimentStore>((set) => ({
  selectedExperimentId: null,
  selectedProjectId: null,
  isProjectSelectorOpen: false,
  setSelectedExperimentId: (id) => set({ selectedExperimentId: id }),
  setSelectedProjectId: (id) => set({ selectedProjectId: id, selectedExperimentId: null }),
  openProjectSelector: () => set({ isProjectSelectorOpen: true }),
  closeProjectSelector: () => set({ isProjectSelectorOpen: false }),
}));
