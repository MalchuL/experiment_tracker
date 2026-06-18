"use client";

import { useState } from "react";
import { GitCompare, Loader2, Maximize2, PencilLine, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExperimentDiffCountBadge } from "@/components/shared/experiment-diff-ui";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  useExperimentHparams,
  useExperimentHparamsQuery,
} from "@/domain/experiments/hooks/experiment-hparams-hook";
import {
  formatHparamsJson,
  parseHparamsJson,
} from "@/domain/experiments/lib/hparams-json";
import { summarizeHparamsDiff } from "@/domain/experiments/lib/hparams-diff";
import type { HparamsDocument } from "@/domain/experiments/types";
import { useToast } from "@/lib/hooks/use-toast";
import { ExperimentHparamsTree } from "./experiment-hparams-tree";

export function ExperimentHparamsPanel({
  experimentId,
  parentExperimentId,
  enabled,
}: {
  experimentId: string;
  parentExperimentId?: string | null;
  enabled: boolean;
}) {
  const { toast } = useToast();
  const {
    data,
    isLoading,
    isError,
    replaceHparams,
    replacePending,
    deleteHparams,
    deletePending,
  } = useExperimentHparams(experimentId, enabled);
  const [editorOpen, setEditorOpen] = useState(false);
  const [replaceConfirmOpen, setReplaceConfirmOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [draft, setDraft] = useState("{}");
  const [parseError, setParseError] = useState<string | null>(null);
  const [pendingDocument, setPendingDocument] = useState<HparamsDocument | null>(null);
  const [showDiffs, setShowDiffs] = useState(true);
  const [expandedOpen, setExpandedOpen] = useState(false);
  const hparams = data?.hparams ?? null;
  const parentQuery = useExperimentHparamsQuery(
    parentExperimentId ?? "",
    enabled && Boolean(parentExperimentId)
  );
  const parentHparams = parentQuery.data?.hparams ?? null;
  const summary = parentHparams
    ? summarizeHparamsDiff(parentHparams, hparams)
    : { added: 0, removed: 0, changed: 0 };

  const openEditor = () => {
    setDraft(formatHparamsJson(hparams));
    setParseError(null);
    setEditorOpen(true);
  };

  const save = async (document: HparamsDocument) => {
    try {
      await replaceHparams(document);
      setEditorOpen(false);
      setReplaceConfirmOpen(false);
      toast({ title: "Hyperparameters updated" });
    } catch {
      toast({ title: "Failed to update hyperparameters", variant: "destructive" });
    }
  };

  const prepareSave = () => {
    try {
      const parsed = parseHparamsJson(draft);
      setParseError(null);
      if (hparams !== null) {
        setPendingDocument(parsed);
        setReplaceConfirmOpen(true);
      } else {
        void save(parsed);
      }
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Invalid JSON.");
    }
  };

  if (!enabled) return null;
  if (isLoading) return <div className="py-8 text-center text-sm text-muted-foreground">Loading hyperparameters...</div>;
  if (isError) return <div className="py-8 text-center text-sm text-destructive">Failed to load hyperparameters.</div>;

  return (
    <div className="w-full min-w-0 max-w-full overflow-hidden">
      <Card className="w-full min-w-0 max-w-full overflow-hidden">
        <CardHeader className="flex min-w-0 flex-row items-center justify-between gap-2 px-3 py-2">
          <CardTitle className="min-w-0 truncate text-xs font-medium text-muted-foreground">
            HParams
          </CardTitle>
          <div className="flex shrink-0 items-center gap-2">
            {parentExperimentId ? (
              <Button
                type="button"
                variant={showDiffs ? "default" : "outline"}
                size="icon"
                className="h-8 w-8"
                onClick={() => setShowDiffs((value) => !value)}
                aria-pressed={showDiffs}
                aria-label={showDiffs ? "Disable hyperparameter diffs" : "Enable hyperparameter diffs"}
                title={showDiffs ? "Disable hyperparameter diffs" : "Enable hyperparameter diffs"}
              >
                <GitCompare className="h-3.5 w-3.5" />
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={() => setExpandedOpen(true)}
              aria-label="Expand hyperparameter diff"
              title="Expand hyperparameter diff"
              data-testid="button-expand-hparams-diff"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
            {hparams !== null ? (
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={() => setDeleteConfirmOpen(true)}
                aria-label="Remove hyperparameters"
                title="Remove hyperparameters"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={openEditor}
              aria-label={hparams === null ? "Add hyperparameters" : "Edit hyperparameters"}
              title={hparams === null ? "Add hyperparameters" : "Edit hyperparameters"}
            >
              <PencilLine className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="w-full min-w-0 max-w-full space-y-2 overflow-hidden px-3 pb-3 pt-0">
          {showDiffs && parentHparams ? (
            <div className="flex flex-wrap gap-1">
              <ExperimentDiffCountBadge status="added" label="Added" value={summary.added} />
              <ExperimentDiffCountBadge status="removed" label="Removed" value={summary.removed} />
              <ExperimentDiffCountBadge status="changed" label="Changed" value={summary.changed} />
            </div>
          ) : null}
          <HparamsView
            hparams={hparams}
            parentHparams={parentHparams}
            showDiffs={showDiffs}
          />
        </CardContent>
      </Card>

      <HparamsExpandedModal
        open={expandedOpen}
        onOpenChange={setExpandedOpen}
        hparams={hparams}
        parentHparams={parentHparams}
        parentExperimentId={parentExperimentId}
        summary={summary}
        showDiffs={showDiffs}
        onShowDiffsChange={setShowDiffs}
      />

      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit hyperparameters</DialogTitle>
            <DialogDescription>Enter a JSON object. Saving replaces the complete current document.</DialogDescription>
          </DialogHeader>
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            className="min-h-80 font-mono text-xs"
            spellCheck={false}
          />
          {parseError ? <p className="text-sm text-destructive">{parseError}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditorOpen(false)}>Cancel</Button>
            <Button type="button" disabled={replacePending} onClick={prepareSave}>
              {replacePending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save hyperparameters
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={replaceConfirmOpen} onOpenChange={setReplaceConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace existing hyperparameters?</AlertDialogTitle>
            <AlertDialogDescription>
              Saving these hyperparameters will replace the existing hyperparameters for this experiment.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={replacePending}>Cancel</AlertDialogCancel>
            <AlertDialogAction disabled={replacePending} onClick={() => pendingDocument && void save(pendingDocument)}>
              Replace
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove hyperparameters?</AlertDialogTitle>
            <AlertDialogDescription>This deletes the current hyperparameter document.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletePending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={deletePending}
              onClick={() => {
                void deleteHparams()
                  .then(() => {
                    setDeleteConfirmOpen(false);
                    toast({ title: "Hyperparameters removed" });
                  })
                  .catch(() => toast({ title: "Failed to remove hyperparameters", variant: "destructive" }));
              }}
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function HparamsView({
  hparams,
  parentHparams,
  showDiffs,
}: {
  hparams: HparamsDocument | null;
  parentHparams: HparamsDocument | null;
  showDiffs: boolean;
}) {
  if (hparams === null && !(showDiffs && parentHparams)) {
    return (
      <div className="rounded-md border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
        No hyperparameters logged for this experiment. Use the SDK or UI to add hyperparameters.
      </div>
    );
  }

  return (
    <ExperimentHparamsTree
      hparams={hparams ?? {}}
      parentHparams={parentHparams}
      showDiffs={showDiffs}
    />
  );
}

function HparamsExpandedModal({
  open,
  onOpenChange,
  hparams,
  parentHparams,
  parentExperimentId,
  summary,
  showDiffs,
  onShowDiffsChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hparams: HparamsDocument | null;
  parentHparams: HparamsDocument | null;
  parentExperimentId?: string | null;
  summary: { added: number; removed: number; changed: number };
  showDiffs: boolean;
  onShowDiffsChange: (showDiffs: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(60rem,calc(100dvh-1rem))] max-w-[min(64rem,calc(100vw-2rem))] flex-col gap-3 p-0">
        <DialogHeader className="border-b px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <DialogTitle>Hyperparameters</DialogTitle>
              <DialogDescription>
                Expanded hyperparameter comparison for this experiment.
              </DialogDescription>
            </div>
            {parentExperimentId ? (
              <Button
                type="button"
                variant={showDiffs ? "default" : "outline"}
                size="icon"
                className="mr-6 h-8 w-8 shrink-0"
                onClick={() => onShowDiffsChange(!showDiffs)}
                aria-pressed={showDiffs}
                aria-label={showDiffs ? "Disable hyperparameter diffs" : "Enable hyperparameter diffs"}
                title={showDiffs ? "Disable hyperparameter diffs" : "Enable hyperparameter diffs"}
              >
                <GitCompare className="h-3.5 w-3.5" />
              </Button>
            ) : null}
          </div>
          {showDiffs && parentHparams ? (
            <div className="flex flex-wrap gap-1 pt-2">
              <ExperimentDiffCountBadge status="added" label="Added" value={summary.added} />
              <ExperimentDiffCountBadge status="removed" label="Removed" value={summary.removed} />
              <ExperimentDiffCountBadge status="changed" label="Changed" value={summary.changed} />
            </div>
          ) : null}
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
          <HparamsView hparams={hparams} parentHparams={parentHparams} showDiffs={showDiffs} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
