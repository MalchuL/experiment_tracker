import { z } from "zod";
import { InsertProject, ProjectMetric, ProjectMetrics, ProjectSetting } from "../types";

export const projectMetricSchema = z.object({
    name: z.string().min(1),
    direction: z.enum(["minimize", "maximize"]),
    aggregation: z.enum(["last", "best", "average"]),
}) satisfies z.ZodType<ProjectMetric>;

export const projectMetricsSchema = z.object({
    trackedMetrics: z.array(projectMetricSchema).default([]),
    displayMetrics: z.array(z.string()).default([]),
}) satisfies z.ZodType<ProjectMetrics>;

export const projectSettingSchema = z.object({
    name: z.string().min(1).max(255),
    description: z.string().default(""),
    type: z.enum(["int", "float", "string", "boolean", "json"]),
    value: z.unknown(),
}) satisfies z.ZodType<ProjectSetting>;

export const insertProjectSchema = z.object({
    name: z.string().min(1, "Name is required").max(100),
    description: z.string().max(500).default(""),
    metrics: projectMetricsSchema.default({
        trackedMetrics: [],
        displayMetrics: [],
    }),
    settings: z.array(projectSettingSchema).default([]),
    teamId: z.string().nullable().optional(),
}) satisfies z.ZodType<InsertProject>;