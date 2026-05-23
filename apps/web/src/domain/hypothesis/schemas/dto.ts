import { z } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";

export const insertHypothesisSchema = z.object({
    projectId: z.string().min(1, "Project is required"),
    title: z.string().min(1, "Title is required").max(ENTITY_NAME_MAX_LEN),
    description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
    author: z.string().min(1, "Author is required").max(ENTITY_NAME_MAX_LEN),
    status: z.enum(["proposed", "testing", "supported", "refuted", "inconclusive"]).default("proposed"),
    targetMetrics: z.array(z.string().max(ENTITY_NAME_MAX_LEN)).default([]),
    baseline: z.string().max(ENTITY_NAME_MAX_LEN).default("root"),
  });