import { ProjectMetric, ProjectSettings } from "./types";

export interface InsertProject {
    name: string;
    description: string;
    owner: string;
    metrics?: ProjectMetric[];
    settings?: ProjectSettings;
    teamId?: string | null;
  }