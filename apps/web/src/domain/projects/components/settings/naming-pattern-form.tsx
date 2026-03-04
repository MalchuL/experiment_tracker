"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { settingsSchema, SettingsFormData } from "../../schemas/settings";
import { Project } from "../../types";

interface NamingPatternFormProps {
  project: Project;
  onSubmit: (data: SettingsFormData) => void;
  isPending: boolean;
}

export function NamingPatternForm({ project, onSubmit, isPending }: NamingPatternFormProps) {
  const namingPatternSetting = project.settings.find(
    (setting) => setting.name === "namingPattern" && setting.type === "string"
  );
  const namingPatternValue =
    typeof namingPatternSetting?.value === "string"
      ? namingPatternSetting.value
      : "{num}_from_{parent}_{change}";

  const form = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      namingPattern: namingPatternValue,
      displayMetrics: project?.metrics?.displayMetrics || [],
    },
    values: {
      namingPattern: namingPatternValue,
      displayMetrics: project?.metrics?.displayMetrics || [],
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="namingPattern"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Pattern Template</FormLabel>
              <FormControl>
                <Input
                  placeholder="{num}_from_{parent}_{change}"
                  data-testid="input-naming-pattern"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Available variables: {"{num}"} (experiment number), {"{parent}"} (parent name), {"{change}"} (what changed)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button
          type="submit"
          disabled={isPending}
          data-testid="button-save-settings"
        >
          Save Settings
        </Button>
      </form>
    </Form>
  );
}

