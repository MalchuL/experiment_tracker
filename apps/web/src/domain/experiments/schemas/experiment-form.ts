import z, { ZodType } from "zod";
import { ExperimentForm } from "../types/form";
import { EXPERIMENT_COLORS } from "./experiments";
import { ExperimentStatus } from "../types/types";

export const experimentFormSchema = z.object({
    name: z.string().min(1, "Name is required"),
    description: z.string().default(""),
    status: z.enum(ExperimentStatus).default("planned"),
    parentExperimentId: z.string().nullable(),
    featuresJson: z.string().default("{}"),
    color: z.string().default(EXPERIMENT_COLORS[0]),
}) satisfies ZodType<ExperimentForm>;