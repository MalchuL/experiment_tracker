import { create } from "zustand";

export interface ExperimentStore {
    id: string;
}

export const experimentStore = create<ExperimentStore>((set) => ({
    selectedExperimentId: null,
    setSelectedExperimentId: (id: string | null) => set({ selectedExperimentId: id }),
}));