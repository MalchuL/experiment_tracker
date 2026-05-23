import { z, ZodType } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";
import { InsertExperiment } from "../types";

export const EXPERIMENT_COLORS: string[] = [
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

const featureNodeSchema: z.ZodType<InsertExperiment["features"] extends (infer Node)[] | undefined ? Node : never> = z.lazy(() =>
    z.object({
        name: z.string().min(1),
        children: z.array(featureNodeSchema).optional(),
    })
);

export const insertExperimentSchema = z.object({
    projectId: z.string().min(1, "Project is required"),
    name: z.string().min(1, "Name is required").max(ENTITY_NAME_MAX_LEN),
    description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
    status: z.enum(["planned", "running", "complete", "failed"]).default("planned"),
    parentExperimentId: z.string().nullable().optional(),
    features: z.array(featureNodeSchema).default([]),
    color: z.string().optional(),
    order: z.number().optional(),
}) satisfies ZodType<InsertExperiment>;
