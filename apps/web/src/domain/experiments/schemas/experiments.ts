import { z, ZodType } from "zod";
import { InsertExperiment } from "../types";

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

export const insertExperimentSchema = z.object({
    projectId: z.string().min(1, "Project is required"),
    name: z.string().min(1, "Name is required").max(100),
    description: z.string().max(1000).default(""),
    status: z.enum(["planned", "running", "complete", "failed"]).default("planned"),
    parentExperimentId: z.string().nullable().optional(),
    features: z.record(z.string(), z.unknown()).default({}),
    gitDiff: z.string().nullable().optional(),
    color: z.string().optional(),
    order: z.number().optional(),
}) satisfies ZodType<InsertExperiment>;