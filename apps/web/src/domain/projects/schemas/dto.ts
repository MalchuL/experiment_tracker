import { z } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";
import { InsertProject, ProjectMetrics, ProjectSetting } from "../types";
import type { ProjectMetric, ProjectDisplayMetric } from "../types";

export const projectMetricSchema = z.object({
    name: z.string().min(1),
    direction: z.enum(["minimize", "maximize"]),
    aggregation: z.enum(["last", "best", "average"]),
    label: z.string().nullable().optional(),
}) satisfies z.ZodType<ProjectMetric>;

const displayKeySchema = z.union([
  z.string(),
  z.object({
    name: z.string(),
    label: z.string().nullable().optional(),
  }),
]) satisfies z.ZodType<ProjectDisplayMetric>;

export const projectMetricsSchema = z.object({
  trackedMetrics: z.array(projectMetricSchema).default([]),
  displayMetrics: z.array(displayKeySchema).default([]),
}) satisfies z.ZodType<ProjectMetrics>;

export const projectSettingSchema = z.object({
    name: z.string().min(1),
    description: z.string().default(""),
    type: z.enum(["int", "float", "string", "boolean", "json"]),
    value: z.unknown(),
}) satisfies z.ZodType<ProjectSetting>;

export const insertProjectSchema = z.object({
    name: z.string().min(1, "Name is required").max(ENTITY_NAME_MAX_LEN),
    description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
    metrics: projectMetricsSchema.default({
        trackedMetrics: [],
        displayMetrics: [],
    }),
    settings: z.array(projectSettingSchema).default([]),
    teamId: z.string().nullable().optional(),
}) satisfies z.ZodType<InsertProject>;