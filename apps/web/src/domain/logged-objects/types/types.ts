export type LoggedObjectType =
  | "image"
  | "video"
  | "audio"
  | "text"
  | "point_cloud_3d";

export interface LoggedObjectEntry {
  timestamp: string;
  step: number;
  name: string;
  object_type: LoggedObjectType;
  path: string;
  metadata: Record<string, string>;
  tags: string[];
}

export interface ExperimentObjects {
  experiment_id: string;
  objects: LoggedObjectEntry[];
}

export interface ProjectObjectsResult {
  data: ExperimentObjects[];
}
