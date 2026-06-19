"use client";

import { useCallback, useMemo, useState, type ReactNode } from "react";
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
import { Plus, FolderKanban, AlertCircle, Users, ChevronDown, RefreshCw } from "lucide-react";
import type { InsertProject, Project } from "@/domain/projects/types";
import { insertProjectSchema } from "@/domain/projects/schemas";
import { useProjects } from "@/domain/projects/hooks";
import { useAuth } from "@/domain/auth/hooks";
import { useTeams } from "@/domain/teams/hooks";
import { CreateTeamModal } from "@/domain/teams/components";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

/** Newest-first within a bucket (matches API ordering after backend sort). */
function sortProjectsNewestFirst(projects: Project[]): Project[] {
  return [...projects].sort((a, b) => {
    const tb = new Date(b.createdAt).getTime();
    const ta = new Date(a.createdAt).getTime();
    return tb - ta;
  });
}

function ProjectGrid({ projects }: { projects: Project[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}

function CollapsibleProjectBucket({
  title,
  description,
  children,
}: {
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Collapsible defaultOpen className="space-y-3">
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="group flex w-full items-center justify-between gap-3 rounded-md py-1 text-left outline-none transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <div className="min-w-0 flex-1 space-y-1">
            <div className="text-lg font-semibold tracking-tight">{title}</div>
            {description ? (
              <div className="text-sm font-normal text-muted-foreground">{description}</div>
            ) : null}
          </div>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden space-y-3">{children}</CollapsibleContent>
    </Collapsible>
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
    isFetching,
    isFetchingNextPage,
    createProject,
    creationIsPending,
    refetch,
    error,
  } = useProjects();

  const isRefreshing = isFetching && !isLoading;
  const handleRefresh = useCallback(() => {
    void refetch();
  }, [refetch]);

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
    for (const t of teamsList ?? []) {
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
      } else if (p.owner?.id === uid) {
        pers.push(p);
      } else {
        shr.push(p);
      }
    }
    for (const [tid, list] of map.entries()) {
      map.set(tid, sortProjectsNewestFirst(list));
    }
    return {
      byTeamId: map,
      personal: sortProjectsNewestFirst(pers),
      shared: sortProjectsNewestFirst(shr),
    };
  }, [projects, user?.id]);

  const teamCreatedAtMsById = useMemo(() => {
    const m = new Map<string, number>();
    for (const t of teamsList ?? []) {
      m.set(t.id, new Date(t.createdAt).getTime());
    }
    return m;
  }, [teamsList]);

  /** Team buckets: newest-created teams first (aligned with GET /teams ordering). */
  const sortedTeamIds = useMemo(() => {
    return Array.from(byTeamId.keys()).sort((a, b) => {
      const ta = teamCreatedAtMsById.get(a);
      const tb = teamCreatedAtMsById.get(b);
      if (ta != null && tb != null && tb !== ta) return tb - ta;
      if (ta != null && tb == null) return -1;
      if (ta == null && tb != null) return 1;
      const na = teamNameById.get(a) ?? a;
      const nb = teamNameById.get(b) ?? b;
      return na.localeCompare(nb);
    });
  }, [byTeamId, teamCreatedAtMsById, teamNameById]);

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

  const onSubmit = useCallback(
    (data: InsertProject) => {
      createMutation(data);
    },
    [createMutation],
  );

  const headerActions = useMemo(() => {
    if (isLoading) return null;
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          disabled={isRefreshing}
          data-testid="button-refresh-projects"
          aria-label="Refresh projects"
        >
          <RefreshCw className={isRefreshing ? "animate-spin" : ""} />
        </Button>
        {!error && (
          <>
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
          </>
        )}
      </div>
    );
  }, [
    isLoading,
    error,
    handleRefresh,
    isRefreshing,
    isDialogOpen,
    form,
    onSubmit,
    creationIsPending,
  ]);

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
        <Button onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={isRefreshing ? "mr-2 h-4 w-4 animate-spin" : "mr-2 h-4 w-4"} />
          Try again
        </Button>
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
              <CollapsibleProjectBucket key={tid} title={title}>
                <ProjectGrid projects={list} />
              </CollapsibleProjectBucket>
            );
          })}

          {personal.length > 0 && (
            <CollapsibleProjectBucket
              title="Personal"
              description="Projects without a team that you own."
            >
              <ProjectGrid projects={personal} />
            </CollapsibleProjectBucket>
          )}

          {shared.length > 0 && (
            <CollapsibleProjectBucket
              title="Shared with you"
              description="Personal projects from others where you were granted access."
            >
              <ProjectGrid projects={shared} />
            </CollapsibleProjectBucket>
          )}

          {isFetchingNextPage && (
            <p className="text-sm text-muted-foreground">Loading more projects...</p>
          )}
        </>
      )}
    </div>
  );
}
