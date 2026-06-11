"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, Loader2, Maximize2, RefreshCw, Trash2, X } from "lucide-react";
import { StructuredArtifactPreview } from "@/components/shared/structured-artifact-preview";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/lib/hooks/use-toast";
import { useFinalArtifactPreview } from "@/domain/experiment-artifacts/hooks";
import { experimentArtifactsService } from "@/domain/experiment-artifacts/service";
import type { NamedExperimentArtifact } from "@/domain/experiment-artifacts/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { cn } from "@/lib/utils";

function buildNamedArtifactDownloadUrl(
  experimentId: string,
  name: string,
  filepath: string,
  disposition: "attachment" | "inline" = "attachment"
): string {
  const params = new URLSearchParams({
    experiment_id: experimentId,
    name,
    filepath,
    disposition,
  });
  return `/api/experiment-artifacts/named/download?${params.toString()}`;
}

export interface FinalArtifactCardProps {
  artifact: NamedExperimentArtifact;
}

export function FinalArtifactCard({ artifact }: FinalArtifactCardProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [expandOpen, setExpandOpen] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

  const { preview, isLoading: previewLoading, isFetching: previewFetching } =
    useFinalArtifactPreview(artifact, open);

  const downloadUrl = buildNamedArtifactDownloadUrl(
    artifact.experimentId,
    artifact.name,
    artifact.filepath,
    "attachment"
  );

  const handleRefresh = async () => {
    await queryClient.invalidateQueries({
      queryKey: [
        QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(artifact.experimentId),
        "preview",
        artifact.name,
        artifact.filepath,
      ],
    });
    toast({ title: "Preview refreshed" });
  };

  const handleDelete = async () => {
    setDeletePending(true);
    try {
      await experimentArtifactsService.deleteTrackedArtifact(
        artifact.experimentId,
        artifact.filepath
      );
      await queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(artifact.experimentId)],
      });
      toast({ title: "Artifact deleted" });
      setDeleteOpen(false);
      setOpen(false);
    } catch {
      toast({ title: "Failed to delete artifact", variant: "destructive" });
    } finally {
      setDeletePending(false);
    }
  };

  return (
    <>
      <Collapsible open={open} onOpenChange={setOpen}>
        <Card className="shadow-none" data-testid={`artifact-card-${artifact.id}`}>
          <CardContent className="space-y-0 p-2.5">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-center gap-1.5 rounded-md py-0.5 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                  aria-label={open ? "Collapse artifact preview" : "Expand artifact preview"}
                  data-testid={`button-expand-artifact-${artifact.id}`}
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center text-muted-foreground">
                    <ChevronDown
                      className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
                    />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate text-sm font-medium">{artifact.name}</span>
                      <Badge variant="outline" className="h-5 shrink-0 px-1.5 text-[10px] font-normal">
                        {artifact.mimeType}
                      </Badge>
                    </div>
                    <p className="truncate text-xs text-muted-foreground" title={artifact.filepath}>
                      {artifact.filepath}
                    </p>
                  </div>
                </button>
              </CollapsibleTrigger>
              <div className="flex shrink-0 items-center gap-0.5">
                {open ? (
                  <>
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8"
                      title="Refresh this preview"
                      aria-label="Refresh this preview"
                      onClick={() => void handleRefresh()}
                    >
                      {previewFetching ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    {!previewLoading && preview ? (
                      <Button
                        type="button"
                        size="icon"
                        variant="outline"
                        className="h-8 w-8"
                        title="Expand fullscreen"
                        aria-label="Expand fullscreen"
                        onClick={() => setExpandOpen(true)}
                      >
                        <Maximize2 className="h-3.5 w-3.5" />
                      </Button>
                    ) : null}
                  </>
                ) : null}
                <Button
                  asChild
                  size="icon"
                  variant="outline"
                  className="h-8 w-8"
                  title="Download"
                  aria-label="Download"
                >
                  <a href={downloadUrl} target="_blank" rel="noreferrer">
                    <Download className="h-3.5 w-3.5" />
                  </a>
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="destructive"
                  className="h-8 w-8"
                  title="Delete"
                  aria-label="Delete artifact"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            <CollapsibleContent className="pt-2">
              {previewLoading ? (
                <p className="text-xs text-muted-foreground">Loading preview…</p>
              ) : (
                <StructuredArtifactPreview filepath={artifact.filepath} preview={preview} />
              )}
            </CollapsibleContent>
          </CardContent>
        </Card>
      </Collapsible>

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this artifact?</AlertDialogTitle>
            <AlertDialogDescription className="break-all">
              This permanently removes{" "}
              <span className="font-medium text-foreground">{artifact.filepath}</span> from the
              experiment. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletePending}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              disabled={deletePending}
              onClick={() => void handleDelete()}
            >
              {deletePending ? "Deleting…" : "Delete"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={expandOpen} onOpenChange={setExpandOpen}>
        <DialogContent className="flex h-[min(100dvh,100vh)] w-[min(100dvw,100vw)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-w-none">
          <DialogHeader className="shrink-0 border-b px-4 py-3 pr-14 text-left">
            <DialogTitle className="truncate text-base">{artifact.name}</DialogTitle>
            <p className="truncate text-xs text-muted-foreground">{artifact.filepath}</p>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-auto bg-muted/20 p-4">
            <StructuredArtifactPreview
              filepath={artifact.filepath}
              preview={preview}
              density="relaxed"
            />
          </div>
          <div className="flex shrink-0 flex-wrap justify-end gap-2 border-t px-4 py-3">
            <Button asChild size="icon" variant="outline" title="Download" aria-label="Download">
              <a href={downloadUrl} target="_blank" rel="noreferrer">
                <Download className="h-4 w-4" />
              </a>
            </Button>
            <Button
              type="button"
              size="icon"
              variant="secondary"
              title="Close"
              aria-label="Close"
              onClick={() => setExpandOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
