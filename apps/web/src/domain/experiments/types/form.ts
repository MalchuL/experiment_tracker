import { ExperimentStatusType } from "./types";

export interface ExperimentForm {
    name: string;
    description: string;
    status: ExperimentStatusType;
    parentExperimentId: string | null;
    featuresJson: string;
    color: string;
}