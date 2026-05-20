import type { PaginatedResponse } from "@/lib/types/pagination";

export type LoggedObjectType =
  | "image"
  | "video"
  | "audio"
  | "text"
  | "point_cloud_3d";

export interface LoggedArtifactEntry {
  timestamp: string;
  step: number;
  name: string;
  artifact_type: LoggedObjectType;
  path: string;
  metadata: Record<string, string>;
  tags: string[];
}

export interface ExperimentArtifactsInfo {
  experiment_id: string;
  artifacts_info: LoggedArtifactEntry[];
}

export interface ArtifactsInfoResult
  extends PaginatedResponse<ExperimentArtifactsInfo> {}

export interface LoggedArtifactSummaryEntry {
  name: string;
  artifact_type: LoggedObjectType;
  steps: number[];
  last_modified: string;
}

export interface ExperimentArtifactsSummary {
  experiment_id: string;
  artifacts_info: LoggedArtifactSummaryEntry[];
}

export interface ArtifactsInfoSummaryResult
  extends PaginatedResponse<ExperimentArtifactsSummary> {}
