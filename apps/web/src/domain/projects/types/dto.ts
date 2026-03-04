import { ProjectMetrics, ProjectSetting } from "./types";

export interface InsertProject {
    name: string;
    description: string;
    metrics?: ProjectMetrics;
    settings?: ProjectSetting[];
    teamId?: string | null;
  }

export interface UpdateProject {
    name?: string;
    description?: string;
    metrics?: ProjectMetrics;
    settings?: ProjectSetting[];
    teamId?: string | null;
  }