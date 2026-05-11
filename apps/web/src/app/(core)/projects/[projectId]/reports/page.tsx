"use client";

import Link from "next/link";
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, FileText, Plus } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ListSkeleton } from "@/components/shared/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useCurrentProject } from "@/domain/projects/hooks";
import { reportsService } from "@/domain/reports/services/reports-service";
import { emptyReportDocument } from "@/domain/reports/lib/report-document";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export default function ProjectReportsPage() {
  const { project, isLoading: projectLoading } = useCurrentProject();
  const projectId = project?.id;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: projectId ? [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] : [],
    queryFn: () => reportsService.listByProject(projectId!),
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!projectId) {
        throw new Error("No project");
      }
      return reportsService.create({
        projectId,
        title: "Untitled report",
        content: emptyReportDocument(),
      });
    },
    onSuccess: (report) => {
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] });
      }
      toast({ title: "Report created", description: "You can rename it in the editor." });
      router.push(FRONTEND_ROUTES.PROJECT_PAGES.REPORT_BY_ID(projectId!, report.id));
    },
    onError: () => {
      toast({
        title: "Could not create report",
        variant: "destructive",
      });
    },
  });

  const onCreate = useCallback(() => {
    createMutation.mutate();
  }, [createMutation]);

  if (!projectId) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="No project selected"
        description="Open a project from the sidebar to manage reports."
      />
    );
  }

  if (projectLoading || isLoading) {
    return (
      <div className="space-y-6 p-6">
        <PageHeader title="Reports" description="Compose rich reports with embedded experiment data" />
        <ListSkeleton />
      </div>
    );
  }

  const items = data?.data ?? [];

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Reports"
        description="Notion-style documents with configurable metric, scalar, and artifact blocks."
        actions={
          <Button size="sm" onClick={onCreate} disabled={createMutation.isPending}>
            <Plus className="mr-1.5 h-4 w-4" />
            New report
          </Button>
        }
      />
      {items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports yet"
          description="Create a report to capture narrative, figures, and experiment context in one place."
          action={
            <Button onClick={onCreate} disabled={createMutation.isPending}>
              Create report
            </Button>
          }
        />
      ) : (
        <ul className="divide-y rounded-lg border border-border bg-card">
          {items.map((row) => (
            <li key={row.id}>
              <Link
                href={FRONTEND_ROUTES.PROJECT_PAGES.REPORT_BY_ID(projectId, row.id)}
                className="flex flex-col gap-0.5 px-4 py-3 transition-colors hover:bg-muted/60"
              >
                <span className="font-medium">{row.title}</span>
                <span className="text-xs text-muted-foreground">
                  Updated {new Date(row.updatedAt).toLocaleString()}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
