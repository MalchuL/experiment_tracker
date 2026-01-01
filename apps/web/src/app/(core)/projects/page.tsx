"use client";

import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateProjectModal } from "@/domain/projects/components/create-project-modal";
import { ProjectCard } from "@/domain/projects/components/project-card";
import { ListSkeleton } from "@/domain/projects/components/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/hooks/use-toast";
import { Plus, FolderKanban } from "lucide-react";
import type { Project, InsertProject } from "@/domain/projects/types";
import { insertProjectSchema } from "@/domain/projects/schemas";
import { useProjects } from "@/domain/projects/hooks";

export default function Projects() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { toast } = useToast();

  const { projects, isLoading, createProject, deleteProject, creationIsPending } = useProjects();

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
          <CreateProjectModal
            isOpen={isDialogOpen}
            onOpenChange={setIsDialogOpen}
            form={form}
            onSubmit={onSubmit}
            creationIsPending={creationIsPending}
          />
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
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={deleteMutation}
            />
          ))}
        </div>
      )}
    </div>
  );
}
