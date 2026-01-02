import { create } from "zustand";

interface ExperimentStoreState {
    selectedExperimentId: string | null;
    setSelectedExperimentId: (id: string | null) => void;
}

export const useExperimentStore = create<ExperimentStoreState>((set) => ({
    selectedExperimentId: null,
    setSelectedExperimentId: (id: string | null) => set({ selectedExperimentId: id }),
}));


