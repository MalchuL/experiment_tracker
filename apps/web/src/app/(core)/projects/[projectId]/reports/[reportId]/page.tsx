"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useExperiments } from "@/domain/experiments/hooks";
import { useCurrentProject } from "@/domain/projects/hooks";
import { emptyReportDocument } from "@/domain/reports/lib/report-document";
import { reportsService } from "@/domain/reports/services/reports-service";
import { ReportRichTextEditor } from "@/domain/reports/tiptap/report-rich-text-editor";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";

const SAVE_DEBOUNCE_MS = 900;

export default function ProjectReportEditorPage() {
  const params = useParams<{ projectId: string; reportId: string }>();
  const projectId = params.projectId;
  const reportId = params.reportId;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { project, isLoading: projectLoading } = useCurrentProject();
  const { experiments, isLoading: experimentsLoading } = useExperiments(projectId);

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: [QUERY_KEYS.REPORTS.BY_ID(reportId)],
    queryFn: () => reportsService.getById(reportId),
    enabled: !!reportId,
  });

  const [title, setTitle] = useState("");
  const [doc, setDoc] = useState<Record<string, unknown>>(emptyReportDocument);
  const lastSavedRef = useRef<{ title: string; doc: string } | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!report) {
      return;
    }
    setTitle(report.title);
    const c = report.content && typeof report.content === "object" ? report.content : emptyReportDocument();
    setDoc(c as Record<string, unknown>);
    lastSavedRef.current = {
      title: report.title,
      doc: JSON.stringify(c),
    };
  }, [report]);

  const experimentOptions = useMemo(
    () => experiments.map((e) => ({ id: e.id, name: e.name })),
    [experiments],
  );

  const saveMutation = useMutation({
    mutationFn: async (payload: { title: string; content: Record<string, unknown> }) => {
      return reportsService.update(reportId, {
        title: payload.title,
        content: payload.content,
      });
    },
    onSuccess: (saved) => {
      lastSavedRef.current = {
        title: saved.title,
        doc: JSON.stringify(saved.content),
      };
      queryClient.setQueryData([QUERY_KEYS.REPORTS.BY_ID(reportId)], saved);
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.REPORTS.BY_PROJECT(projectId)] });
      }
    },
    onError: () => {
      toast({ title: "Save failed", variant: "destructive" });
    },
  });

  const scheduleSave = useCallback(
    (nextTitle: string, nextDoc: Record<string, unknown>) => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      saveTimerRef.current = setTimeout(() => {
        const serialized = JSON.stringify(nextDoc);
        if (
          lastSavedRef.current &&
          lastSavedRef.current.title === nextTitle &&
          lastSavedRef.current.doc === serialized
        ) {
          return;
        }
        saveMutation.mutate({ title: nextTitle, content: nextDoc });
      }, SAVE_DEBOUNCE_MS);
    },
    [saveMutation],
  );

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, []);

  const onDocChange = useCallback(
    (json: Record<string, unknown>) => {
      setDoc(json);
      scheduleSave(title, json);
    },
    [scheduleSave, title],
  );

  const onTitleBlur = useCallback(() => {
    if (!report) {
      return;
    }
    const trimmed = title.trim() || "Untitled report";
    if (trimmed !== title) {
      setTitle(trimmed);
    }
    scheduleSave(trimmed, doc);
  }, [doc, report, scheduleSave, title]);

  const manualSave = useCallback(() => {
    saveMutation.mutate({ title: title.trim() || "Untitled report", content: doc });
  }, [doc, saveMutation, title]);

  if (!projectId || !reportId) {
    return null;
  }

  const loading = projectLoading || reportLoading || experimentsLoading;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-border bg-background px-4 py-2">
        <Button variant="ghost" size="sm" asChild>
          <Link href={FRONTEND_ROUTES.PROJECT_PAGES.REPORTS(projectId)}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Reports
          </Link>
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="ml-auto gap-1"
          onClick={manualSave}
          disabled={saveMutation.isPending || loading}
        >
          <Save className="h-4 w-4" />
          Save now
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4 md:p-6">
        {loading || !report ? (
          <div className="text-sm text-muted-foreground">Loading report…</div>
        ) : (
          <div className="mx-auto flex max-w-4xl flex-col gap-4">
            <div className="space-y-1">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onBlur={onTitleBlur}
                className="h-12 border-none bg-transparent px-0 text-2xl font-semibold tracking-tight shadow-none focus-visible:ring-0"
                aria-label="Report title"
              />
              {project?.name ? (
                <p className="text-sm text-muted-foreground">{project.name}</p>
              ) : null}
            </div>
            <ReportRichTextEditor
              key={report.id}
              projectId={projectId}
              experiments={experimentOptions}
              initialContent={doc}
              onChange={onDocChange}
            />
          </div>
        )}
      </div>
    </div>
  );
}
