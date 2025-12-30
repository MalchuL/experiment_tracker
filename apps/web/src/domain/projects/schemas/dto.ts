import { z } from "zod";
import { InsertProject, ProjectMetric, ProjectSettings } from "../types";

export const projectMetricSchema = z.object({
    name: z.string().min(1),
    direction: z.enum(["minimize", "maximize"]),
    aggregation: z.enum(["last", "best", "average"]),
}) satisfies z.ZodType<ProjectMetric>;

export const projectSettingsSchema = z.object({
    namingPattern: z.string().default("{num}_from_{parent}_{change}"),
    displayMetrics: z.array(z.string()).default([]),
}) satisfies z.ZodType<ProjectSettings>;

export const insertProjectSchema = z.object({
    name: z.string().min(1, "Name is required").max(100),
    description: z.string().max(500).default(""),
    owner: z.string().min(1, "Owner is required"),
    metrics: z.array(projectMetricSchema).default([]),
    settings: projectSettingsSchema.default({
        namingPattern: "{num}_from_{parent}_{change}",
        displayMetrics: [],
    }),
    teamId: z.string().nullable().optional(),
}) satisfies z.ZodType<InsertProject>;