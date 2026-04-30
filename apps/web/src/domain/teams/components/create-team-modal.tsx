"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useCreateTeam } from "@/domain/teams/hooks";
import { useToast } from "@/lib/hooks/use-toast";

const createTeamSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).optional().default(""),
});

export type CreateTeamFormValues = z.infer<typeof createTeamSchema>;

export interface CreateTeamModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateTeamModal({ open, onOpenChange }: CreateTeamModalProps) {
  const { toast } = useToast();
  const createTeam = useCreateTeam();

  const form = useForm<CreateTeamFormValues>({
    resolver: zodResolver(createTeamSchema as any),
    defaultValues: { name: "", description: "" },
  });

  const onSubmit = (values: CreateTeamFormValues) => {
    createTeam.mutate(
      { name: values.name, description: values.description || null },
      {
        onSuccess: () => {
          onOpenChange(false);
          form.reset();
          toast({ title: "Team created", description: "You can add projects under this team from New Project." });
        },
        onError: () => {
          toast({ title: "Could not create team", variant: "destructive" });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create team</DialogTitle>
          <DialogDescription>
            You will be the team owner and can invite members with roles (Maintainer, Developer, Guest).
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="ML Platform" data-testid="input-create-team-name" {...field} />
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
                    <Textarea placeholder="Optional" data-testid="input-create-team-description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createTeam.isPending} data-testid="button-submit-create-team">
                {createTeam.isPending ? "Creating…" : "Create team"}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
