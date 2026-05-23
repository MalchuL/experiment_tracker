"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ENTITY_DESCRIPTION_MAX_LEN,
  ENTITY_NAME_MAX_LEN,
} from "@/lib/validation/entity-limits";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Save, Palette } from "lucide-react";
import { EXPERIMENT_COLORS } from "@/domain/experiments/schemas";
import type { Experiment } from "@/domain/experiments/types";
import { ColorList } from "./color-list";

const experimentEditSchema = z.object({
  name: z.string().min(1, "Name is required").max(ENTITY_NAME_MAX_LEN),
  description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
  color: z.string().default(EXPERIMENT_COLORS[0]),
});

type ExperimentEditFormData = z.infer<typeof experimentEditSchema>;

export type ExperimentEditSavePayload = ExperimentEditFormData & {
  parentExperimentId?: string | null;
};

interface ExperimentEditFormProps {
  experiment: Experiment;
  onSave: (data: ExperimentEditSavePayload) => void;
  isSaving?: boolean;
  /** When set together with `savedParentExperimentId`, parent is included in Save and can show the button when only parent differs. */
  draftParentExperimentId?: string | null;
  savedParentExperimentId?: string | null;
}

export function ExperimentEditForm({
  experiment,
  onSave,
  isSaving = false,
  draftParentExperimentId,
  savedParentExperimentId,
}: ExperimentEditFormProps) {
  const form = useForm<ExperimentEditFormData>({
    resolver: zodResolver(experimentEditSchema as any),
    defaultValues: {
      name: experiment.name,
      description: experiment.description || "",
      color: experiment.color || EXPERIMENT_COLORS[0],
    },
  });

  // Update form when experiment changes
  useEffect(() => {
    form.reset({
      name: experiment.name,
      description: experiment.description || "",
      color: experiment.color || EXPERIMENT_COLORS[0],
    });
  }, [experiment.id, experiment.name, experiment.description, experiment.color, form]);

  const onSubmit = (data: ExperimentEditFormData) => {
    const includeParent =
      draftParentExperimentId !== undefined &&
      savedParentExperimentId !== undefined;
    if (includeParent) {
      onSave({
        ...data,
        parentExperimentId: draftParentExperimentId ?? null,
      });
    } else {
      onSave(data);
    }
  };

  const isParentDirty =
    draftParentExperimentId !== undefined &&
    savedParentExperimentId !== undefined
      ? (draftParentExperimentId ?? null) !== (savedParentExperimentId ?? null)
      : false;

  const hasChanges = form.formState.isDirty || isParentDirty;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel htmlFor="name">Name</FormLabel>
              <FormControl>
                <Input
                  id="name"
                  placeholder="Experiment name"
                  data-testid="input-name"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel htmlFor="description">Description</FormLabel>
              <FormControl>
                <Textarea
                  id="description"
                  placeholder="Add experiment description..."
                  className="min-h-[80px] resize-none"
                  data-testid="input-description"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="color"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="flex items-center gap-2">
                <Palette className="w-4 h-4" />
                Color
              </FormLabel>
                  <div className="flex items-center gap-2">
                      <ColorList currentColor={field.value}
                          useColorPalette={true}
                          onColorChange={field.onChange}
                          colors={EXPERIMENT_COLORS} />
                  </div>
                  <FormMessage />
              </FormItem>
          )}
        />

        {hasChanges && (
          <Button
            type="submit"
            size="sm"
            disabled={isSaving}
            data-testid="button-save-experiment"
            className="w-full"
          >
            <Save className="w-4 h-4 mr-1" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
        )}
      </form>
    </Form>
  );
}

