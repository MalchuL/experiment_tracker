"use client";

import { useCallback, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Upload } from "lucide-react";
import { FileDropzone } from "@/components/shared/file-upload/dropzone";
import { useFileDropzone } from "@/components/shared/file-upload/use-file-dropzone";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  buildFinalArtifactFilepath,
  defaultDisplayNameFromFile,
  getFileExtension,
} from "@/domain/experiment-artifacts/lib/artifact-filepath";
import { experimentArtifactsService } from "@/domain/experiment-artifacts/service";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

export function ExperimentArtifactUploadCard({ experimentId }: { experimentId: string }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(true);
  const [displayName, setDisplayName] = useState("");
  const [filepath, setFilepath] = useState("final/");
  const [pendingExtension, setPendingExtension] = useState("");
  const [autoSyncFilepath, setAutoSyncFilepath] = useState(true);

  const uploadMutation = useMutation({
    mutationFn: async ({
      file,
      name,
      path,
    }: {
      file: File;
      name: string;
      path: string;
    }) => {
      const artifact = await experimentArtifactsService.upsertTrackedArtifact(experimentId, file, {
        name,
        filepath: path,
      });
      return artifact;
    },
    onSuccess: (artifact) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEYS.ARTIFACTS.NAMED_BY_EXPERIMENT(experimentId)],
      });
      toast({
        title: "Artifact uploaded",
        description: artifact.filepath,
      });
      setDisplayName("");
      setFilepath("final/");
      setPendingExtension("");
      setAutoSyncFilepath(true);
      resetFileInput();
    },
    onError: (error: Error) => {
      toast({
        title: "Upload failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const uploadFile = useCallback(
    (file: File) => {
      const extension = getFileExtension(file.name);
      setPendingExtension(extension);

      const name = displayName.trim() || defaultDisplayNameFromFile(file);
      if (!displayName.trim()) {
        setDisplayName(name);
      }

      const path = autoSyncFilepath
        ? buildFinalArtifactFilepath(name, extension)
        : filepath.trim() || buildFinalArtifactFilepath(name, extension);

      if (autoSyncFilepath) {
        setFilepath(path);
      }

      void uploadMutation.mutateAsync({ file, name, path });
    },
    [autoSyncFilepath, displayName, filepath, uploadMutation]
  );

  const handleFiles = useCallback(
    (files: FileList) => {
      const file = files[0];
      if (!file) {
        return;
      }
      uploadFile(file);
    },
    [uploadFile]
  );

  const {
    fileInputRef,
    handleBoxClick,
    handleDragOver,
    handleDrop,
    handleFileSelect,
    resetFileInput,
  } = useFileDropzone(handleFiles);

  const handleDisplayNameChange = (value: string) => {
    setDisplayName(value);
    if (autoSyncFilepath) {
      setFilepath(buildFinalArtifactFilepath(value, pendingExtension));
    }
  };

  const handleFilepathChange = (value: string) => {
    setAutoSyncFilepath(false);
    setFilepath(value);
  };

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="shadow-none" data-testid="artifact-upload-card">
        <CardContent className="space-y-0 p-2.5">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-1.5 rounded-md py-0.5 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                aria-label={open ? "Collapse upload form" : "Expand upload form"}
                data-testid="button-expand-artifact-upload"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center text-muted-foreground">
                  <ChevronDown
                    className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
                  />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <Upload className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm font-medium">Upload artifact</span>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">
                    Drag and drop or browse to upload a tracked final artifact
                  </p>
                </div>
              </button>
            </CollapsibleTrigger>
          </div>

          <CollapsibleContent className="space-y-3 pt-2">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor={`artifact-upload-name-${experimentId}`} className="text-xs">
                  Display name
                </Label>
                <Input
                  id={`artifact-upload-name-${experimentId}`}
                  value={displayName}
                  onChange={(event) => handleDisplayNameChange(event.target.value)}
                  placeholder="e.g. model checkpoint"
                  className="h-8 text-sm"
                  disabled={uploadMutation.isPending}
                  data-testid="input-artifact-upload-name"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`artifact-upload-path-${experimentId}`} className="text-xs">
                  Stored filepath
                </Label>
                <Input
                  id={`artifact-upload-path-${experimentId}`}
                  value={filepath}
                  onChange={(event) => handleFilepathChange(event.target.value)}
                  placeholder="final/…"
                  className="h-8 font-mono text-sm"
                  disabled={uploadMutation.isPending}
                  data-testid="input-artifact-upload-path"
                />
                <p className="text-[11px] text-muted-foreground">
                  {autoSyncFilepath
                    ? pendingExtension
                      ? `Auto: final/name${pendingExtension}`
                      : "Auto-updates from display name; extension added on file select"
                    : "Manual override — won't update when display name changes"}
                </p>
              </div>
            </div>

            <FileDropzone
              fileInputRef={fileInputRef}
              handleBoxClick={handleBoxClick}
              handleDragOver={handleDragOver}
              handleDrop={handleDrop}
              handleFileSelect={handleFileSelect}
              inputId={`artifact-upload-file-${experimentId}`}
              inputTestId="input-artifact-upload-file"
              title="Drop artifact file here"
              browseLabel="Drag and drop, or click to browse"
              compact
              disabled={uploadMutation.isPending}
              isUploading={uploadMutation.isPending}
            />

            <p className="text-xs text-muted-foreground">
              By default the stored path follows <code className="text-[11px]">final/&lt;name&gt;</code>{" "}
              plus the file extension. You can override it manually; uploading to the same path
              replaces an existing artifact.
            </p>
          </CollapsibleContent>
        </CardContent>
      </Card>
    </Collapsible>
  );
}
