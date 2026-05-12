"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SimpleReportEditor } from "@/domain/reports/components/simple-report-editor";
import { reportsService } from "@/domain/reports";
import type { ReportDocumentJSON } from "@/domain/reports/types";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

export default function ProjectReportEditorPage() {
  const params = useParams<{ projectId: string; reportId: string }>();
  const projectId = params.projectId;
  const reportId = params.reportId;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState("");
  const [contentJson, setContentJson] = useState<ReportDocumentJSON | null>(null);
  const [editorNonce, setEditorNonce] = useState(0);
  const initializedDraftForReportId = useRef<string | null>(null);

  const { data: report, isLoading, isError } = useQuery({
    queryKey: [QUERY_KEYS.REPORTS.BY_ID(reportId)],
    queryFn: () => reportsService.getById(reportId),
    enabled: Boolean(reportId),
  });

  useEffect(() => {
    initializedDraftForReportId.current = null;
  }, [reportId]);

  useEffect(() => {
    if (!report) return;
    if (initializedDraftForReportId.current === reportId) return;
    initializedDraftForReportId.current = reportId;
    setTitle(report.title);
    setContentJson(report.content);
    setEditorNonce((n) => n + 1);
  }, [report, reportId]);

  const saveMutation = useMutation({
    mutationFn: () =>
      reportsService.update(reportId, {
        title: title.trim() || "Untitled report",
        content: contentJson ?? undefined,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData([QUERY_KEYS.REPORTS.BY_ID(reportId)], updated);
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] });
      }
      setTitle(updated.title);
      setContentJson(updated.content);
      setEditorNonce((n) => n + 1);
      toast({ title: "Saved", description: "Report changes were saved." });
    },
    onError: () => {
      toast({
        title: "Save failed",
        description: "You may not have edit permission or the network failed.",
        variant: "destructive",
      });
    },
  });

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">Could not load this report.</p>
        <Link
          className="mt-2 inline-block text-sm font-medium text-primary underline underline-offset-4"
          href={FRONTEND_ROUTES.PROJECT_PAGES.REPORTS(projectId)}
        >
          Back to reports
        </Link>
      </div>
    );
  }

  if (isLoading || !report || contentJson === null) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 p-6 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading report…
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href={FRONTEND_ROUTES.PROJECT_PAGES.REPORTS(projectId)} aria-label="Back to reports">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader title="Edit report" description="Rich text is stored as JSON on the server." />
      </div>

      <div className="flex max-w-3xl flex-col gap-3">
        <label className="text-sm font-medium" htmlFor="report-title">
          Title
        </label>
        <Input
          id="report-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
        />
      </div>

      <div className="min-h-0 flex-1 max-w-3xl w-full">
        <SimpleReportEditor
          editorKey={`${reportId}-${editorNonce}`}
          documentJson={contentJson}
          onDocumentChange={setContentJson}
        />
      </div>

      <div className="flex gap-2 pb-4">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending || !title.trim()}
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving…
            </>
          ) : (
            "Save"
          )}
        </Button>
      </div>
    </div>
  );
}
