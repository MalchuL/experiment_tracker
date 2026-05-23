import { z } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";

export const basicInfoSchema = z.object({
  name: z.string().min(1, "Project name is required").max(ENTITY_NAME_MAX_LEN),
  description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).optional(),
});

export type BasicInfoFormData = z.infer<typeof basicInfoSchema>;
