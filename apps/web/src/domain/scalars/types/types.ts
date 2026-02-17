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

export interface ScalarsPointsResult {
  data: ExperimentScalarsPoints[];
}

export interface LastLoggedExperimentsRequest {
  experiment_ids: string[] | null;
}

export interface LastLoggedExperiment {
  experiment_id: string;
  last_modified: string;
}

export interface LastLoggedExperimentsResult {
  data: LastLoggedExperiment[];
}
