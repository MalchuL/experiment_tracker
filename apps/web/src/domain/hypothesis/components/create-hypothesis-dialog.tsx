"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useCreateHypothesis } from "../hooks";
import { insertHypothesisSchema } from "../schemas";
import { InsertHypothesis } from "../types/dto";
import type { Project } from "@/domain/projects/types";
import { HypothesisStatus } from "../types/types";

interface CreateHypothesisDialogProps {
  projectId: string;
  projects?: Project[];
  trigger?: React.ReactNode;
}

export function CreateHypothesisDialog({
  projectId,
  projects,
  trigger,
}: CreateHypothesisDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { createHypothesis, isPending } = useCreateHypothesis(projectId, {
    onSuccess: () => {
      setIsOpen(false);
      form.reset();
    },
  });

  const form = useForm<InsertHypothesis>({
    resolver: zodResolver(insertHypothesisSchema as any),
    defaultValues: {
      projectId: projectId || "",
      title: "",
      description: "",
      author: "researcher",
      status: "proposed",
      targetMetrics: [],
      baseline: "root",
    },
  });

  const onSubmit = (data: InsertHypothesis) => {
    createHypothesis(data);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {!!trigger || (
          <Button data-testid="button-create-hypothesis">
            <Plus className="w-4 h-4 mr-2" />
            New Hypothesis
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Hypothesis</DialogTitle>
          <DialogDescription>
            Define a research claim to test through experiments.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="projectId"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Project</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger data-testid="select-project">
                        <SelectValue placeholder="Select a project" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {projects?.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., AdamW with lr=1e-4 converges faster than SGD"
                      data-testid="input-hypothesis-title"
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
                      placeholder="Describe the expected impact and reasoning..."
                      className="resize-none"
                      data-testid="input-hypothesis-description"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="author"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Author</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Your name"
                      data-testid="input-hypothesis-author"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger data-testid="select-status">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={HypothesisStatus.PROPOSED}>Proposed</SelectItem>
                      <SelectItem value={HypothesisStatus.TESTING}>Testing</SelectItem>
                      <SelectItem value={HypothesisStatus.SUPPORTED}>Supported</SelectItem>
                      <SelectItem value={HypothesisStatus.REFUTED}>Refuted</SelectItem>
                      <SelectItem value={HypothesisStatus.INCONCLUSIVE}>Inconclusive</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isPending}
                data-testid="button-submit-hypothesis"
              >
                {isPending ? "Creating..." : "Create Hypothesis"}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

