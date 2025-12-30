import { MetricDirectionType, MetricAggregationType } from "@/domain/metrics/types";

export interface ProjectMetric {
    name: string;
    direction: MetricDirectionType;
    aggregation: MetricAggregationType;
  }
  
  export interface ProjectSettings {
    namingPattern: string;
    displayMetrics: string[];
  }
  

export interface Project {
    id: string;
    name: string;
    description: string;
    owner: string;
    createdAt: string;
    experimentCount: number;
    hypothesisCount: number;
    metrics: ProjectMetric[];
    settings: ProjectSettings;
    teamId?: string | null;
    teamName?: string | null;
  }