import { z } from "zod";

export const basicInfoSchema = z.object({
  name: z.string().min(1, "Project name is required"),
  description: z.string().optional(),
  owner: z.string().optional(),
});

const displayKeySchema = z.union([
  z.string(),
  z.object({
    name: z.string(),
    label: z.string().nullable().optional(),
  }),
]);

export const settingsSchema = z.object({
  namingPattern: z.string().default("{num}_from_{parent}_{change}"),
  displayMetrics: z.array(displayKeySchema),
});

export type BasicInfoFormData = z.infer<typeof basicInfoSchema>;
export type SettingsFormData = z.infer<typeof settingsSchema>;

