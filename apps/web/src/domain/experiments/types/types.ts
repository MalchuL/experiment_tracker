export const ExperimentStatus = {
    PLANNED: "planned",
    RUNNING: "running",
    COMPLETE: "complete",
    FAILED: "failed",
  } as const;
  
  export type ExperimentStatusType = typeof ExperimentStatus[keyof typeof ExperimentStatus];

export interface Experiment {
    id: string;
    projectId: string;
    name: string;
    description: string;
    status: ExperimentStatusType;
    parentExperimentId: string | null;
    rootExperimentId: string | null;
    features: Record<string, unknown>;
    featuresDiff: Record<string, unknown> | null;
    gitDiff: string | null;
    progress: number;
    color: string;
    order: number;
    createdAt: string;
    startedAt: string | null;
    completedAt: string | null;
  }
  