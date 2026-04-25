import type { PaginatedResponse } from "@/lib/types/pagination";

export interface ScalarSeries {
  x: number[];
  y: number[];
}

export interface StepTags {
  step: number;
  scalar_names: string[];
  tags: string[];
}

export interface ExperimentScalarsPoints {
  experiment_id: string;
  scalars: Record<string, ScalarSeries>;
  tags?: StepTags[] | null;
}

export interface ScalarsPointsResult
  extends PaginatedResponse<ExperimentScalarsPoints> {}

export interface LastLoggedExperimentsRequest {
  experiment_ids: string[] | null;
}

export interface LastLoggedExperiment {
  experiment_id: string;
  last_modified: string;
}

export interface LastLoggedExperimentsResult
  extends PaginatedResponse<LastLoggedExperiment> {}

export interface ScalarSavedView {
  id: string;
  projectId: string;
  name: string;
  query: string;
  createdAt: string;
  updatedAt: string;
}

export type SyncMode = "all" | "x-only" | "y-only" | "independent";

export interface ChartDomain {
  x: [number, number] | null;
  y: [number, number] | null;
}

export interface LoggedObjectRef {
  path: string;
  metadata: Record<string, string>;
  timestamp: string;
}

export interface LoggedObjectNameGroup {
  steps: number[];
  byExperiment: Record<string, Record<number, LoggedObjectRef>>;
}

export type LoggedObjectGroups = Record<string, Record<string, LoggedObjectNameGroup>>;
