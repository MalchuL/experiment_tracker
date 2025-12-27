import { sql } from "drizzle-orm";
import { pgTable, text, varchar, integer, timestamp, jsonb, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export const ExperimentStatus = {
  PLANNED: "planned",
  RUNNING: "running",
  COMPLETE: "complete",
  FAILED: "failed",
} as const;

export type ExperimentStatusType = typeof ExperimentStatus[keyof typeof ExperimentStatus];

export const HypothesisStatus = {
  PROPOSED: "proposed",
  TESTING: "testing",
  SUPPORTED: "supported",
  REFUTED: "refuted",
  INCONCLUSIVE: "inconclusive",
} as const;

export type HypothesisStatusType = typeof HypothesisStatus[keyof typeof HypothesisStatus];

export const MetricDirection = {
  MINIMIZE: "minimize",
  MAXIMIZE: "maximize",
} as const;

export type MetricDirectionType = typeof MetricDirection[keyof typeof MetricDirection];

export const MetricAggregation = {
  LAST: "last",
  BEST: "best",
  AVERAGE: "average",
} as const;

export type MetricAggregationType = typeof MetricAggregation[keyof typeof MetricAggregation];

export const EXPERIMENT_COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#6366f1", // indigo
] as const;

export interface ProjectMetric {
  name: string;
  direction: MetricDirectionType;
  aggregation: MetricAggregationType;
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
}

export interface InsertProject {
  name: string;
  description: string;
  owner: string;
  metrics?: ProjectMetric[];
}

export const projectMetricSchema = z.object({
  name: z.string().min(1),
  direction: z.enum(["minimize", "maximize"]),
  aggregation: z.enum(["last", "best", "average"]),
});

export const insertProjectSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).default(""),
  owner: z.string().min(1, "Owner is required"),
  metrics: z.array(projectMetricSchema).default([]),
});

export interface Experiment {
  id: string;
  projectId: string;
  name: string;
  status: ExperimentStatusType;
  parentExperimentId: string | null;
  rootExperimentId: string | null;
  features: Record<string, unknown>;
  featuresDiff: Record<string, unknown> | null;
  gitDiff: string | null;
  progress: number;
  color: string;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface InsertExperiment {
  projectId: string;
  name: string;
  status?: ExperimentStatusType;
  parentExperimentId?: string | null;
  features?: Record<string, unknown>;
  gitDiff?: string | null;
  color?: string;
}

export const insertExperimentSchema = z.object({
  projectId: z.string().min(1, "Project is required"),
  name: z.string().min(1, "Name is required").max(100),
  status: z.enum(["planned", "running", "complete", "failed"]).default("planned"),
  parentExperimentId: z.string().nullable().optional(),
  features: z.record(z.unknown()).default({}),
  gitDiff: z.string().nullable().optional(),
  color: z.string().optional(),
});

export interface Metric {
  id: string;
  experimentId: string;
  name: string;
  value: number;
  step: number;
  direction: MetricDirectionType;
  createdAt: string;
}

export interface InsertMetric {
  experimentId: string;
  name: string;
  value: number;
  step?: number;
  direction?: MetricDirectionType;
}

export const insertMetricSchema = z.object({
  experimentId: z.string().min(1, "Experiment is required"),
  name: z.string().min(1, "Name is required"),
  value: z.number(),
  step: z.number().default(0),
  direction: z.enum(["minimize", "maximize"]).default("minimize"),
});

export interface Hypothesis {
  id: string;
  projectId: string;
  title: string;
  description: string;
  author: string;
  status: HypothesisStatusType;
  targetMetrics: string[];
  baseline: string;
  createdAt: string;
  updatedAt: string;
}

export interface InsertHypothesis {
  projectId: string;
  title: string;
  description: string;
  author: string;
  status?: HypothesisStatusType;
  targetMetrics?: string[];
  baseline?: string;
}

export const insertHypothesisSchema = z.object({
  projectId: z.string().min(1, "Project is required"),
  title: z.string().min(1, "Title is required").max(200),
  description: z.string().max(1000).default(""),
  author: z.string().min(1, "Author is required"),
  status: z.enum(["proposed", "testing", "supported", "refuted", "inconclusive"]).default("proposed"),
  targetMetrics: z.array(z.string()).default([]),
  baseline: z.string().default("root"),
});

export interface ExperimentHypothesis {
  experimentId: string;
  hypothesisId: string;
}

export interface Evidence {
  id: string;
  hypothesisId: string;
  experimentId: string;
  metricName: string;
  baselineValue: number;
  experimentValue: number;
  delta: number;
  normalizedDelta: number;
  direction: MetricDirectionType;
  confidenceScore: number;
  createdAt: string;
}

export interface DashboardStats {
  totalProjects: number;
  totalExperiments: number;
  runningExperiments: number;
  completedExperiments: number;
  failedExperiments: number;
  totalHypotheses: number;
  supportedHypotheses: number;
  refutedHypotheses: number;
}

export interface ExperimentMetricValue {
  experimentId: string;
  metricName: string;
  value: number | null;
}
