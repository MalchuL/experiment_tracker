import { ExperimentStatusType, type FeatureNode } from "./types";

export interface InsertExperiment {
    projectId: string;
    name: string;
    description?: string;
    status?: ExperimentStatusType;
    parentExperimentId?: string | null;
    features?: FeatureNode[];
    color?: string;
    order?: number;
    tags?: string[];
}

export interface UpdateExperiment {
    name?: string;
    description?: string;
    status?: ExperimentStatusType;
    parentExperimentId?: string | null;
    features?: FeatureNode[];
    color?: string;
    order?: number;
    tags?: string[];
}
