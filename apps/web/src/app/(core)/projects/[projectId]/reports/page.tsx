"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, FileText, Loader2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useCurrentProject } from "@/domain/projects/hooks";
import { reportsService } from "@/domain/reports";
import type { ProjectReportSummary } from "@/domain/reports/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { format, formatDistanceToNow } from "date-fns";

/** Same pattern as experiment sidebar / details: `MMM d, yyyy, HH:mm` in local time. */
function getDefaultNewReportTitle(): string {
  return `Untitled Report ${format(new Date(), "MMM d, yyyy, HH:mm")}`;
}

export default function ProjectReportsPage() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [reportPendingDelete, setReportPendingDelete] =
    useState<ProjectReportSummary | null>(null);

  const { data, isLoading: listLoading } = useQuery({
    queryKey: projectId ? [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] : [],
    queryFn: () => reportsService.listByProject(projectId!),
    enabled: Boolean(projectId),
  });

  const deleteMutation = useMutation({
    mutationFn: (reportId: string) => reportsService.delete(reportId),
    onSuccess: (_, reportId) => {
      queryClient.removeQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_ID(reportId)] });
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] });
      }
      setReportPendingDelete(null);
      toast({ title: "Report deleted", description: "The report was removed from this project." });
    },
    onError: () => {
      toast({
        title: "Could not delete report",
        description: "Check that you have permission or try again.",
        variant: "destructive",
      });
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      reportsService.create({
        projectId: projectId!,
        title: getDefaultNewReportTitle(),
      }),
    onSuccess: (report) => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] });
      }
      toast({ title: "Report created", description: "You can rename it on the next page." });
      router.push(FRONTEND_ROUTES.PROJECT_PAGES.REPORT_BY_ID(projectId!, report.id));
    },
    onError: () => {
      toast({
        title: "Could not create report",
        description: "Check that you have permission to create reports.",
        variant: "destructive",
      });
    },
  });

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-8rem)] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <h2 className="text-lg font-medium">No project selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Select a project from the sidebar to manage reports.
        </p>
      </div>
    );
  }

  if (projectLoading || listLoading) {
    return (
      <div className="space-y-6 p-6">
        <PageHeader title="Reports" description="Project notes and write-ups" />
        <ListSkeleton />
      </div>
    );
  }

  const rows = data?.data ?? [];

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Reports"
        description="Create rich-text pages stored with this project."
        actions={
          <Button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            size="sm"
          >
            <Plus className="mr-2 h-4 w-4" />
            New report
          </Button>
        }
      />

      {rows.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports yet"
          description="Create a report to capture summaries, methods, or experiment notes."
          action={
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              <Plus className="mr-2 h-4 w-4" />
              New report
            </Button>
          }
        />
      ) : (
        <>
          <ul className="divide-y rounded-lg border bg-card">
            {rows.map((r) => (
              <li key={r.id} className="flex items-stretch">
                <Link
                  href={FRONTEND_ROUTES.PROJECT_PAGES.REPORT_BY_ID(projectId, r.id)}
                  className="flex min-w-0 flex-1 flex-col gap-1 px-4 py-3 transition-colors hover:bg-muted/60"
                >
                  <span className="font-medium truncate">{r.title}</span>
                  <span className="text-xs text-muted-foreground">
                    Updated{" "}
                    {formatDistanceToNow(new Date(r.updatedAt), { addSuffix: true })}
                  </span>
                </Link>
                <div className="flex shrink-0 items-center border-l px-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive"
                    aria-label={`Delete report: ${r.title}`}
                    disabled={deleteMutation.isPending}
                    onClick={(e) => {
                      e.preventDefault();
                      setReportPendingDelete(r);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>

          <AlertDialog
            open={reportPendingDelete !== null}
            onOpenChange={(open) => {
              if (!open) setReportPendingDelete(null);
            }}
          >
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this report?</AlertDialogTitle>
                <AlertDialogDescription>
                  {reportPendingDelete ? (
                    <>
                      <span className="font-medium text-foreground">
                        {reportPendingDelete.title}
                      </span>{" "}
                      will be permanently removed. This cannot be undone.
                    </>
                  ) : null}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={deleteMutation.isPending}>
                  Cancel
                </AlertDialogCancel>
                <Button
                  type="button"
                  variant="destructive"
                  disabled={deleteMutation.isPending || !reportPendingDelete}
                  onClick={() => {
                    if (reportPendingDelete) {
                      deleteMutation.mutate(reportPendingDelete.id);
                    }
                  }}
                >
                  {deleteMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Deleting…
                    </>
                  ) : (
                    "Delete report"
                  )}
                </Button>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </>
      )}
    </div>
  );
}
