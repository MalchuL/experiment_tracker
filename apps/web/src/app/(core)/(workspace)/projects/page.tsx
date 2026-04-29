"use client";

import { useCallback, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageHeader } from "@/components/shared/page-header";
import { useWorkspaceHeaderActions } from "@/components/shared/workspace-shell";
import { EmptyState } from "@/components/shared/empty-state";
import { CreateProjectModal } from "@/domain/projects/components/create-project-modal";
import { ProjectCard } from "@/domain/projects/components/project-card";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/lib/hooks/use-toast";
import { Plus, FolderKanban, AlertCircle, Users } from "lucide-react";
import type { InsertProject, Project } from "@/domain/projects/types";
import { insertProjectSchema } from "@/domain/projects/schemas";
import { useProjects } from "@/domain/projects/hooks";
import { useAuth } from "@/domain/auth/hooks";
import { useTeams } from "@/domain/teams/hooks";
import { CreateTeamModal } from "@/domain/teams/components";

function ProjectGrid({
  projects,
  onDelete,
}: {
  projects: Project[];
  onDelete: (id: string) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} onDelete={onDelete} />
      ))}
    </div>
  );
}

export default function Projects() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [teamDialogOpen, setTeamDialogOpen] = useState(false);
  const { toast } = useToast();
  const { user } = useAuth();
  const { data: teamsList } = useTeams();

  const {
    projects,
    isLoading,
    isFetchingNextPage,
    createProject,
    deleteProject,
    creationIsPending,
    error,
  } = useProjects();

  const form = useForm<InsertProject>({
    resolver: zodResolver(insertProjectSchema as any),
    defaultValues: {
      name: "",
      description: "",
      teamId: null,
    },
  });

  const teamNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const t of teamsList?.data ?? []) {
      m.set(t.id, t.name);
    }
    return m;
  }, [teamsList]);

  const { byTeamId, personal, shared } = useMemo(() => {
    const map = new Map<string, Project[]>();
    const pers: Project[] = [];
    const shr: Project[] = [];
    const uid = user?.id;
    for (const p of projects) {
      if (p.teamId) {
        const list = map.get(p.teamId) ?? [];
        list.push(p);
        map.set(p.teamId, list);
      } else if (p.owner.id === uid) {
        pers.push(p);
      } else {
        shr.push(p);
      }
    }
    return { byTeamId: map, personal: pers, shared: shr };
  }, [projects, user?.id]);

  const sortedTeamIds = useMemo(() => {
    return Array.from(byTeamId.keys()).sort((a, b) => {
      const na = teamNameById.get(a) ?? a;
      const nb = teamNameById.get(b) ?? b;
      return na.localeCompare(nb);
    });
  }, [byTeamId, teamNameById]);

  const createMutation = useCallback(
    (data: InsertProject) => {
      createProject(data, {
        onSuccess: () => {
          setIsDialogOpen(false);
          form.reset({ name: "", description: "", teamId: null });
          toast({
            title: "Project created",
            description: "Your new project has been created successfully.",
          });
        },
        onError: () => {
          toast({
            title: "Error",
            description: "Failed to create project. Please try again.",
            variant: "destructive",
          });
        },
      });
    },
    [createProject, form, toast],
  );

  const deleteMutation = useCallback(
    (id: string) => {
      deleteProject(id, {
        onSuccess: () => {
          toast({
            title: "Project deleted",
            description: "The project has been deleted successfully.",
          });
        },
        onError: () => {
          toast({
            title: "Error",
            description: "Failed to delete project. Please try again.",
            variant: "destructive",
          });
        },
      });
    },
    [deleteProject, toast],
  );

  const onSubmit = useCallback(
    (data: InsertProject) => {
      createMutation(data);
    },
    [createMutation],
  );

  const headerActions = useMemo(() => {
    if (isLoading || error) return null;
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="outline" onClick={() => setTeamDialogOpen(true)} data-testid="button-create-team">
          <Users className="mr-2 h-4 w-4" />
          New team
        </Button>
        <CreateProjectModal
          isOpen={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          form={form}
          onSubmit={onSubmit}
          creationIsPending={creationIsPending}
        />
      </div>
    );
  }, [isLoading, error, isDialogOpen, form, onSubmit, creationIsPending]);

  useWorkspaceHeaderActions(headerActions);

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
        <PageHeader title="Projects" description="Manage your research projects" />
        <ListSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto max-w-screen-2xl space-y-6 p-6">
        <PageHeader title="Projects" description="Manage your research projects" />
        <EmptyState
          icon={AlertCircle}
          title="Error"
          description="Failed to load projects. Please try again."
        />
        <Button onClick={() => window.location.reload()}>Reload</Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-screen-2xl space-y-8 p-6">
      <CreateTeamModal open={teamDialogOpen} onOpenChange={setTeamDialogOpen} />
      <PageHeader
        title="Projects"
        description="Grouped by team, your personal workspace, and projects shared with you"
      />

      {!projects || projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          description="Create a team to group projects, or start with a personal project."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="outline" onClick={() => setTeamDialogOpen(true)} data-testid="button-empty-create-team">
                <Users className="mr-2 h-4 w-4" />
                New team
              </Button>
              <Button onClick={() => setIsDialogOpen(true)} data-testid="button-empty-create-project">
                <Plus className="mr-2 h-4 w-4" />
                Create project
              </Button>
            </div>
          }
        />
      ) : (
        <>
          {sortedTeamIds.map((tid) => {
            const list = byTeamId.get(tid) ?? [];
            if (list.length === 0) return null;
            const title = teamNameById.get(tid) ?? "Team";
            return (
              <section key={tid} className="space-y-3">
                <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
                <ProjectGrid projects={list} onDelete={deleteMutation} />
              </section>
            );
          })}

          {personal.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold tracking-tight">Personal</h2>
              <p className="text-sm text-muted-foreground">Projects without a team that you own.</p>
              <ProjectGrid projects={personal} onDelete={deleteMutation} />
            </section>
          )}

          {shared.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold tracking-tight">Shared with you</h2>
              <p className="text-sm text-muted-foreground">
                Personal projects from others where you were granted access.
              </p>
              <ProjectGrid projects={shared} onDelete={deleteMutation} />
            </section>
          )}

          {isFetchingNextPage && (
            <p className="text-sm text-muted-foreground">Loading more projects...</p>
          )}
        </>
      )}
    </div>
  );
}
