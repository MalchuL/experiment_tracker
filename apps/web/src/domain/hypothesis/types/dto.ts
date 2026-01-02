import { HypothesisStatusType } from "./types";

export interface InsertHypothesis {
    projectId: string;
    title: string;
    description?: string;
    author?: string;
    status?: HypothesisStatusType;
    targetMetrics?: string[];
    baseline?: string;
  }