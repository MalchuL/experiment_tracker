import { create } from "zustand";

interface ExperimentStore {
  selectedExperimentId: string | null;
  selectedProjectId: string | null;
  setSelectedExperimentId: (id: string | null) => void;
  setSelectedProjectId: (id: string | null) => void;
}

export const useExperimentStore = create<ExperimentStore>((set) => ({
  selectedExperimentId: null,
  selectedProjectId: null,
  setSelectedExperimentId: (id) => set({ selectedExperimentId: id }),
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
}));
