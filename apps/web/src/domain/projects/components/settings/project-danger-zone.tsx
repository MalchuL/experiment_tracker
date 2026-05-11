"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { projectsService } from "@/domain/projects/services";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import {
  formatCategoryCleanupErrors,
  formatDeletionOutcomeDescription,
} from "@/lib/format-satellite-toast";
import { bytesFrom, formatBytes } from "@/lib/format-storage-usage";
import { useToast } from "@/lib/hooks/use-toast";
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

  const usageQuery = useQuery({
    queryKey: ["project-usage", projectId],
    queryFn: () => projectsService.getUsage(projectId),
    enabled: zoneOpen && Boolean(projectId),
  });

  const [cleanCategory, setCleanCategory] = useState<(typeof PROJECT_USAGE_KEYS)[number] | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

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
    onError: () => {
      toast({ title: "Cleanup failed", variant: "destructive" });
    },
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
      onError: () => toast({ title: "Delete failed", variant: "destructive" }),
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
    </>
  );
}
