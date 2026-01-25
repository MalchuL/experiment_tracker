import { MetricDirectionType, MetricAggregationType } from "@/domain/metrics/types";
import { User } from "@/shared/types/user";

export interface ProjectMetric {
    name: string;
    direction: MetricDirectionType;
    aggregation: MetricAggregationType;
  }
  
  export interface ProjectSettings {
    namingPattern: string;
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
    metrics: ProjectMetric[];
    settings: ProjectSettings;
    teamId?: string | null;
    teamName?: string | null;
  }