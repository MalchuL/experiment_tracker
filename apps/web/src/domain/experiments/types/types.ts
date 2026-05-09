export const ExperimentStatus = {
    PLANNED: "planned",
    RUNNING: "running",
    COMPLETE: "complete",
    FAILED: "failed",
  } as const;
  
export type ExperimentStatusType = typeof ExperimentStatus[keyof typeof ExperimentStatus];

export interface SatelliteStepDto {
  ok: boolean;
  skipped?: boolean;
  errorMessage?: string | null;
}

export interface CategoryCleanupResultEntry {
  category: string;
  result: Record<string, unknown>;
}

export interface CategoryCleanupErrorEntry {
  category: string;
  error: string;
}

export interface CategoryCleanupResponse {
  success: boolean;
  partial: boolean;
  /** Success-step count; when detailed=false, ``results`` may be empty while this is set. */
  resultCount: number;
  results: CategoryCleanupResultEntry[];
  errors: CategoryCleanupErrorEntry[];
}

/** Same wire shape as category cleanup / hard deletes (experiment, project, team, admin user). */
export type ExperimentDeleteResponse = CategoryCleanupResponse;

export interface UsageBytesCount {
  count: number;
  bytes: number;
}

export interface ExperimentUsageSnapshots {
  count: number;
  bytes: number;
  known: boolean;
}

export interface ExperimentScalarsUsage {
  rows: number;
  bytes: number;
}

export interface ExperimentUsageTotal {
  bytes: number;
}

export interface ExperimentUsage {
  experimentId: string;
  projectId: string;
  experimentArtifacts: UsageBytesCount;
  atStepArtifacts: UsageBytesCount;
  snapshots: ExperimentUsageSnapshots;
  scalars: ExperimentScalarsUsage;
  total: ExperimentUsageTotal;
}

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
  