"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { basicInfoSchema, BasicInfoFormData } from "../../schemas/settings";
import { Project } from "../../types";

interface BasicInfoFormProps {
  project: Project;
  onSubmit: (data: BasicInfoFormData) => void;
  isPending: boolean;
}

function ownerDisplay(project: Project): string {
  const o = project.owner;
  if (!o) return "";
  return o.displayName || o.email || o.id;
}

export function BasicInfoForm({ project, onSubmit, isPending }: BasicInfoFormProps) {
  const form = useForm<BasicInfoFormData>({
    resolver: zodResolver(basicInfoSchema as never),
    defaultValues: {
      name: project?.name || "",
      description: project?.description || "",
    },
    values: {
      name: project?.name || "",
      description: project?.description || "",
    },
  });

  const ownerLabel = ownerDisplay(project);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Project Name</FormLabel>
              <FormControl>
                <Input
                  placeholder="My ML Project"
                  data-testid="input-project-name"
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
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Describe your project..."
                  className="resize-none"
                  data-testid="input-project-description"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="space-y-2">
          <FormLabel>Owner</FormLabel>
          <div
            className="rounded-md border border-input bg-muted/50 px-3 py-2 text-sm text-foreground shadow-xs"
            data-testid="display-project-owner"
            aria-readonly="true"
          >
            {ownerLabel || "—"}
          </div>
          <p className="text-xs text-muted-foreground">Owner cannot be changed here.</p>
        </div>
        <Button
          type="submit"
          disabled={isPending}
          data-testid="button-save-basic-info"
        >
          Save Project Info
        </Button>
      </form>
    </Form>
  );
}

