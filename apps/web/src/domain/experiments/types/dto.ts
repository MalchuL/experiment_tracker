import { ExperimentStatusType } from "./types";

export interface InsertExperiment {
    projectId: string;
    name: string;
    description?: string;
    status?: ExperimentStatusType;
    parentExperimentId?: string | null;
    features?: Record<string, unknown>;
    gitDiff?: string | null;
    color?: string;
    order?: number;
}

export interface UpdateExperiment {
    name?: string;
    description?: string;
    status?: ExperimentStatusType;
    parentExperimentId?: string | null;
    features?: Record<string, unknown>;
    gitDiff?: string | null;
    color?: string;
    order?: number;
}