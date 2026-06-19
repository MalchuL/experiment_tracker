"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useProject } from "@/domain/projects/hooks/project-hook";
import { projectMembersService } from "@/domain/projects/services/project-members-service";
import { projectsService } from "@/domain/projects/services";
import { teamsService } from "@/domain/teams/services";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import {
  formatCategoryCleanupErrors,
  formatDeletionOutcomeDescription,
} from "@/lib/format-satellite-toast";
import { bytesFrom, formatBytes } from "@/lib/format-storage-usage";
import { useToast } from "@/lib/hooks/use-toast";
import { getErrorMessage } from "@/lib/api/error-response";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

const PROJECT_USAGE_KEYS = ["projectArtifacts", "snapshots", "experimentBuckets", "scalars"] as const;

const PROJECT_CLEANUP_LABELS: Record<(typeof PROJECT_USAGE_KEYS)[number], string> = {
  projectArtifacts: "project artifacts (shared CAS blobs)",
  snapshots: "project snapshots",
  experimentBuckets: "per-experiment bucket storage",
  scalars: "scalars and step-logged artifact metadata (ClickHouse)",
};

export function ProjectDangerZone({ projectId }: { projectId: string }) {
  const { toast } = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { deleteProject, deleteIsPending } = useProject(projectId);
  const [zoneOpen, setZoneOpen] = useState(false);
  const projectQuery = useQuery({
    queryKey: [QUERY_KEYS.PROJECTS.GET_BY_ID(projectId)],
    queryFn: () => projectsService.getById(projectId),
  });
  const teamsQuery = useQuery({
    queryKey: ["project-transfer-teams"],
    queryFn: () => teamsService.listAll(),
    enabled: zoneOpen,
  });

  const usageQuery = useQuery({
    queryKey: ["project-usage", projectId],
    queryFn: () => projectsService.getUsage(projectId),
    enabled: zoneOpen && Boolean(projectId),
  });

  const [cleanCategory, setCleanCategory] = useState<(typeof PROJECT_USAGE_KEYS)[number] | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [destinationTeamId, setDestinationTeamId] = useState("");
  const [teamTransferOpen, setTeamTransferOpen] = useState(false);
  const [ownerTarget, setOwnerTarget] = useState("");
  const [ownerTransferOpen, setOwnerTransferOpen] = useState(false);

  const invalidateProject = () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.LIST] });
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECTS.GET_BY_ID(projectId)] });
  };

  const cleanupMutation = useMutation({
    mutationFn: (category: string) => projectsService.cleanupCategory(projectId, category),
    onSuccess: (result) => {
      void usageQuery.refetch();
      setCleanCategory(null);
      const hasErrors = result.errors.length > 0;
      toast({
        title: hasErrors ? "Cleanup finished with errors" : "Cleanup finished",
        description: hasErrors
          ? formatCategoryCleanupErrors(result.errors)
          : "No satellite errors.",
        variant: hasErrors ? "destructive" : "default",
      });
    },
    onError: (error) => {
      toast({
        title: "Cleanup failed",
        description: getErrorMessage(error, "The selected project data could not be cleaned."),
        variant: "destructive",
      });
    },
  });

  const teamTransferMutation = useMutation({
    mutationFn: () => projectsService.changeTeam(projectId, destinationTeamId || null),
    onSuccess: () => {
      setTeamTransferOpen(false);
      invalidateProject();
      void projectQuery.refetch();
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId)] });
      toast({ title: "Project team changed" });
    },
    onError: (error) =>
      toast({
        title: "Team change failed",
        description: getErrorMessage(error, "The project team could not be changed."),
        variant: "destructive",
      }),
  });

  const ownerTransferMutation = useMutation({
    mutationFn: async () => {
      const target = ownerTarget.trim();
      const ownerId = target.includes("@")
        ? (await projectMembersService.lookupUser(projectId, target)).id
        : target;
      return projectsService.changeOwner(projectId, ownerId);
    },
    onSuccess: () => {
      setOwnerTransferOpen(false);
      setOwnerTarget("");
      invalidateProject();
      void projectQuery.refetch();
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PROJECT_MEMBERS.LIST(projectId)] });
      toast({ title: "Project owner changed" });
    },
    onError: (error) =>
      toast({
        title: "Ownership transfer failed",
        description: getErrorMessage(error, "Project ownership could not be transferred."),
        variant: "destructive",
      }),
  });

  const handleConfirmCleanupCategory = () => {
    if (cleanCategory) cleanupMutation.mutate(cleanCategory);
  };

  const handleConfirmDeleteProject = () => {
    void deleteProject({
      onDeleteSuccess: (result) => {
        setDeleteOpen(false);
        invalidateProject();
        toast({
          title: result.success ? "Project deleted" : "Project deleted (warnings)",
          description: result.success ? "No errors reported." : formatDeletionOutcomeDescription(result),
          variant: result.success ? "default" : "destructive",
        });
        router.push(FRONTEND_ROUTES.PROJECTS);
      },
      onError: (error) =>
        toast({
          title: "Delete failed",
          description: getErrorMessage(error, "The project could not be deleted."),
          variant: "destructive",
        }),
    });
  };

  return (
    <>
      <Collapsible open={zoneOpen} onOpenChange={setZoneOpen}>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:space-y-0">
            <div className="space-y-1.5">
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Danger zone
              </CardTitle>
              <CardDescription>
                Irreversible or disruptive actions. Expand to load storage usage, then confirm each
                step.
              </CardDescription>
            </div>
            <CollapsibleTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5 self-start sm:self-auto"
              >
                {zoneOpen ? (
                  <>
                    <ChevronUp className="h-4 w-4" />
                    Collapse
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4" />
                    Expand
                  </>
                )}
              </Button>
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent className="overflow-hidden">
            <CardContent className="space-y-8 pt-0">
              <section className="space-y-3">
                <div>
                  <h3 className="text-sm font-medium">Storage cleanup</h3>
                  <p className="text-sm text-muted-foreground">
                    Removes data for a single category from satellites (object storage / ClickHouse).
                    Confirm before cleaning.
                  </p>
                </div>
                {usageQuery.isFetching && !usageQuery.data ? (
                  <p className="text-sm text-muted-foreground">Loading usage…</p>
                ) : usageQuery.data ? (
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                    {PROJECT_USAGE_KEYS.map((key) => (
                      <div key={key} className="rounded-md border bg-background p-3">
                        <p className="text-xs text-muted-foreground">{key}</p>
                        <p className="text-lg font-semibold">
                          {formatBytes(bytesFrom(usageQuery.data[key]))}
                        </p>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="mt-2"
                          onClick={() => setCleanCategory(key)}
                        >
                          Clean…
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Usage is not available.</p>
                )}
              </section>

              <section className="space-y-3 border-t border-destructive/20 pt-6">
                <div>
                  <h3 className="text-sm font-medium">Project assignment</h3>
                  <p className="text-sm text-muted-foreground">
                    Changing the team immediately changes inherited access. Team projects follow the
                    team owner.
                  </p>
                  <p className="text-xs text-muted-foreground">
                    You must be allowed to edit the project, remove projects from its current team,
                    and create projects in the destination team.
                  </p>
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <label className="space-y-1 text-sm">
                    <span className="block text-muted-foreground">Destination</span>
                    <select
                      className="border-input bg-background h-9 min-w-[14rem] rounded-md border px-2"
                      value={destinationTeamId}
                      onChange={(event) => setDestinationTeamId(event.target.value)}
                    >
                      <option value="">Standalone (Personal Project)</option>
                      {(teamsQuery.data ?? []).map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button type="button" variant="outline" onClick={() => setTeamTransferOpen(true)}>
                    Change team…
                  </Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Current team:{" "}
                    {projectQuery.data?.teamId ? (
                      <Link
                        href={FRONTEND_ROUTES.TEAM_BY_ID(projectQuery.data.teamId)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-foreground underline underline-offset-4"
                      >
                        {projectQuery.data.teamName ?? projectQuery.data.teamId}
                      </Link>
                    ) : (
                      <span className="font-semibold text-foreground">
                        Standalone (Personal Project)
                      </span>
                    )}
                  </p>
                  <div className="flex flex-wrap items-end gap-2">
                    <label className="space-y-1 text-sm">
                      <span className="block text-muted-foreground">New owner email or UUID</span>
                      <input
                        className="border-input bg-background h-9 min-w-[18rem] rounded-md border px-3"
                        value={ownerTarget}
                        disabled={Boolean(projectQuery.data?.teamId)}
                        onChange={(event) => setOwnerTarget(event.target.value)}
                      />
                    </label>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={Boolean(projectQuery.data?.teamId) || !ownerTarget.trim()}
                      onClick={() => setOwnerTransferOpen(true)}
                    >
                      Change owner…
                    </Button>
                  </div>
                  {projectQuery.data?.teamId && (
                    <p className="text-sm text-muted-foreground">
                      Ownership follows the team owner while this project belongs to a team.
                    </p>
                  )}
                </div>
              </section>

              <section className="space-y-3 border-t border-destructive/20 pt-6">
                <div>
                  <h3 className="text-sm font-medium">Delete project</h3>
                  <p className="text-sm text-muted-foreground">
                    Permanently removes this project and related satellite data where possible.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="destructive" onClick={() => setDeleteOpen(true)}>
                    Delete project…
                  </Button>
                </div>
              </section>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <AlertDialog open={cleanCategory !== null} onOpenChange={(o) => !o && setCleanCategory(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Clean {cleanCategory ? PROJECT_CLEANUP_LABELS[cleanCategory] : "storage"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes stored data for this category. Other categories are not
              affected. You cannot undo this from the UI.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={cleanupMutation.isPending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={cleanupMutation.isPending || cleanCategory === null}
              onClick={handleConfirmCleanupCategory}
            >
              {cleanupMutation.isPending ? "Cleaning…" : "Yes, clean this category"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this project permanently?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the project and related data according to server rules. This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteIsPending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={deleteIsPending}
              onClick={handleConfirmDeleteProject}
            >
              {deleteIsPending ? "Deleting…" : "Delete project"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={teamTransferOpen} onOpenChange={setTeamTransferOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Change this project&apos;s team?</AlertDialogTitle>
            <AlertDialogDescription>
              Inherited access will change immediately. Destination:{" "}
              {destinationTeamId
                ? (teamsQuery.data ?? []).find((team) => team.id === destinationTeamId)?.name ??
                  destinationTeamId
                : "Standalone (Personal Project)"}
              . This requires permission to remove the project from its current team and create it
              in the destination team when those teams apply.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={teamTransferMutation.isPending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={teamTransferMutation.isPending}
              onClick={() => teamTransferMutation.mutate()}
            >
              {teamTransferMutation.isPending ? "Changing…" : "Change team"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={ownerTransferOpen} onOpenChange={setOwnerTransferOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Transfer project ownership?</AlertDialogTitle>
            <AlertDialogDescription>
              The new owner will receive full project permissions. The current owner keeps existing
              direct access.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={ownerTransferMutation.isPending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={ownerTransferMutation.isPending}
              onClick={() => ownerTransferMutation.mutate()}
            >
              {ownerTransferMutation.isPending ? "Transferring…" : "Transfer ownership"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
