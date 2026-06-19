import type { PaginatedResponse } from "@/lib/types/pagination";

export type ScalarWireValue = number | "nan" | "inf" | "-inf";

export type ScalarValueKind = "finite" | "nan" | "inf" | "-inf";

export interface ScalarSeries {
  x: number[];
  y: ScalarWireValue[];
}

export interface ScalarPointValue {
  original: ScalarWireValue;
  smoothed: ScalarWireValue;
}

export interface ScalarChartPoint {
  step: number;
  [experimentId: string]: ScalarWireValue | ScalarPointValue | null;
}

export type ScalarHoverMode = "compare" | "visible" | "nearest";

export interface ScalarPointSelection {
  experimentId: string;
  experimentName: string;
  metricName: string;
  step: number;
  originalValue: ScalarWireValue;
  smoothedValue: ScalarWireValue;
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

export type ScalarsPointsResult = PaginatedResponse<ExperimentScalarsPoints>;

export interface ScalarNamesResult {
  scalar_names: string[];
}

export interface LastLoggedExperimentsRequest {
  experiment_ids: string[] | null;
}

export interface LastLoggedExperiment {
  experiment_id: string;
  last_modified: string;
}

export type LastLoggedExperimentsResult = PaginatedResponse<LastLoggedExperiment>;

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
  path?: string;
  metadata?: Record<string, string>;
  timestamp?: string;
  lastModified?: string;
}

export interface LoggedObjectNameGroup {
  steps: number[];
  byExperiment: Record<string, Record<number, LoggedObjectRef>>;
}

export type LoggedObjectGroups = Record<string, Record<string, LoggedObjectNameGroup>>;

export interface ArtifactViewItem {
  id: string;
  artifactType: string;
  name: string;
  label: string;
}
