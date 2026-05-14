import z, { ZodType } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";
import { ExperimentForm } from "../types/form";
import { EXPERIMENT_COLORS } from "./experiments";
import { ExperimentStatus } from "../types";

export const experimentFormSchema = z.object({
    name: z.string().min(1, "Name is required").max(ENTITY_NAME_MAX_LEN),
    description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
    status: z.enum(ExperimentStatus).default("planned"),
    parentExperimentId: z.string().nullable(),
    featuresJson: z.string().default("{}"),
    color: z.string().default(EXPERIMENT_COLORS[0]),
}) satisfies ZodType<ExperimentForm>;