import { z } from "zod";

export const insertHypothesisSchema = z.object({
    projectId: z.string().min(1, "Project is required"),
    title: z.string().min(1, "Title is required").max(200),
    description: z.string().max(1000).default(""),
    author: z.string().min(1, "Author is required"),
    status: z.enum(["proposed", "testing", "supported", "refuted", "inconclusive"]).default("proposed"),
    targetMetrics: z.array(z.string()).default([]),
    baseline: z.string().default("root"),
  });