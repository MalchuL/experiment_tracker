"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Download, Maximize2, RefreshCw, Trash2, X } from "lucide-react";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/lib/hooks/use-toast";
import { experimentArtifactsService } from "@/domain/experiment-artifacts/service";
import type { NamedArtifactPreview, NamedExperimentArtifact } from "@/domain/experiment-artifacts/types";
import { QUERY_KEYS } from "@/lib/constants/query-keys";

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
  preview: NamedArtifactPreview | undefined;
}

export function FinalArtifactCard({ artifact, preview }: FinalArtifactCardProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [expandOpen, setExpandOpen] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

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
    } catch {
      toast({ title: "Failed to delete artifact", variant: "destructive" });
    } finally {
      setDeletePending(false);
    }
  };

  return (
    <>
      <Card>
        <CardContent className="space-y-2 pt-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{artifact.name}</span>
                <Badge variant="outline">{artifact.mimeType}</Badge>
              </div>
              <p className="break-all text-sm text-muted-foreground">{artifact.filepath}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-1 sm:pt-0">
              <Button
                type="button"
                size="icon"
                variant="outline"
                title="Refresh this preview"
                aria-label="Refresh this preview"
                onClick={() => void handleRefresh()}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="outline"
                title="Expand"
                aria-label="Expand fullscreen"
                onClick={() => setExpandOpen(true)}
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button asChild size="icon" variant="outline" title="Download" aria-label="Download">
                <a href={downloadUrl} target="_blank" rel="noreferrer">
                  <Download className="h-4 w-4" />
                </a>
              </Button>
              <Button
                type="button"
                size="icon"
                variant="destructive"
                title="Delete"
                aria-label="Delete artifact"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <StructuredArtifactPreview filepath={artifact.filepath} preview={preview} />
        </CardContent>
      </Card>

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
