import { MetricDirectionType, MetricAggregationType } from "@/domain/metrics/types";
import { User } from "@/shared/types/user";

export interface ProjectMetric {
    name: string;
    direction: MetricDirectionType;
    aggregation: MetricAggregationType;
  }

export type ProjectSettingType = "int" | "float" | "string" | "boolean" | "json";

export interface ProjectSetting {
  name: string;
  description: string;
  type: ProjectSettingType;
  value: unknown;
}

export interface ProjectMetrics {
  trackedMetrics: ProjectMetric[];
  displayMetrics: string[];
}
  

export type ProjectOwner = Pick<User, "id" | "email" | "displayName">;

export interface Project {
    id: string;
    name: string;
    description: string;
    owner: ProjectOwner;
    createdAt: string;
    experimentCount: number;
    hypothesisCount: number;
    metrics: ProjectMetrics;
    settings: ProjectSetting[];
    teamId?: string | null;
    teamName?: string | null;
  }