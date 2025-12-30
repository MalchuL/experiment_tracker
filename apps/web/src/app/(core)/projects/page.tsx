"use client";

import { useCallback, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/domain/projects/components/loading-skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/lib/hooks/use-toast";
import { Plus, FolderKanban, FlaskConical, Lightbulb, MoreVertical, Calendar } from "lucide-react";
import type { Project, InsertProject } from "@/domain/projects/types";
import { insertProjectSchema } from "@/domain/projects/schemas";
import { format } from "date-fns";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProjects } from "@/domain/projects/hooks";

export default function Projects() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();

  const { projects, isLoading, create: createProject, delete: deleteProject, creationIsPending } = useProjects();

  const form = useForm<InsertProject>({
    resolver: zodResolver(insertProjectSchema as any),
    defaultValues: {
      name: "",
      description: "",
      owner: "researcher",
    },
  });
  // Create project mutation
  const createMutation = useCallback((data: InsertProject) => {
    createProject(data, {
      onSuccess: () => {
        setIsDialogOpen(false);
        form.reset();
        toast({
          title: "Project created",
          description: "Your new project has been created successfully.",
        });
      },
      onError: (error) => {
        toast({
          title: "Error",
          description: "Failed to create project. Please try again.",
          variant: "destructive",
        });
      },
    });
  }, [createProject]);
 
  // Delete project mutation
  const deleteMutation = useCallback((id: string) => {
    deleteProject(id, {
      onSuccess: () => {
        toast({
          title: "Project deleted",
          description: "The project has been deleted successfully.",
        });
      },
      onError: (error) => {
        toast({
          title: "Error",
          description: "Failed to delete project. Please try again.",
          variant: "destructive",
        });
      },
    });
  }, [deleteProject]);

  const onSubmit = (data: InsertProject) => {
    createMutation(data);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Projects" description="Manage your research projects" />
        <ListSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        description="Manage your research projects and experiments"
        actions={
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="button-create-project">
                <Plus className="w-4 h-4 mr-2" />
                New Project
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Project</DialogTitle>
                <DialogDescription>
                  Create a new research project to organize your experiments.
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
                          <Input 
                            placeholder="e.g., ViT Training on ImageNet" 
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
                            placeholder="Describe the research direction..."
                            className="resize-none"
                            data-testid="input-project-description"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="owner"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Owner</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="Your name or team" 
                            data-testid="input-project-owner"
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button 
                      type="submit" 
                      disabled={creationIsPending}
                      data-testid="button-submit-project"
                    >
                      {creationIsPending ? "Creating..." : "Create Project"}
                    </Button>
                  </div>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        }
      />

      {!projects || projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          description="Create your first project to start tracking experiments and testing hypotheses."
          action={
            <Button onClick={() => setIsDialogOpen(true)} data-testid="button-empty-create-project">
              <Plus className="w-4 h-4 mr-2" />
              Create Project
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card 
                className="hover-elevate active-elevate-2 cursor-pointer h-full"
                data-testid={`card-project-${project.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-md bg-primary/10">
                        <FolderKanban className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-medium truncate">{project.name}</h3>
                        <p className="text-xs text-muted-foreground">{project.owner}</p>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            e.preventDefault();
                            deleteMutation(project.id);
                          }}
                          data-testid={`button-delete-project-${project.id}`}
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  
                  {project.description && (
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <FlaskConical className="w-3 h-3" />
                      <span>{project.experimentCount} experiments</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Lightbulb className="w-3 h-3" />
                      <span>{project.hypothesisCount} hypotheses</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 text-xs text-muted-foreground mt-3 pt-3 border-t">
                    <Calendar className="w-3 h-3" />
                    <span>Created {format(new Date(project.createdAt), "MMM d, yyyy")}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
