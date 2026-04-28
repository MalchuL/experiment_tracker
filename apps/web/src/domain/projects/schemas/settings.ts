import { z } from "zod";

export const basicInfoSchema = z.object({
  name: z.string().min(1, "Project name is required"),
  description: z.string().optional(),
  owner: z.string().optional(),
});

export type BasicInfoFormData = z.infer<typeof basicInfoSchema>;
