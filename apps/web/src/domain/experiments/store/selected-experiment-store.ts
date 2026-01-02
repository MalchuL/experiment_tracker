import { create } from "zustand";

interface SelectedExperimentStoreState {
    selectedExperimentId: string | null;
    setSelectedExperimentId: (id: string | null) => void;
}

export const useSelectedExperimentStore = create<SelectedExperimentStoreState>((set) => ({
    selectedExperimentId: null,
    setSelectedExperimentId: (id: string | null) => set({ selectedExperimentId: id }),
}));


