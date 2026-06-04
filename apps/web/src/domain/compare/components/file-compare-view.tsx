"use client";

import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, GitCompare, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SNAPSHOT_PREVIEW_MAX_BYTES } from "@/lib/constants/snapshot-preview";
import { formatBytes } from "@/lib/format-storage-usage";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { useToast } from "@/lib/hooks/use-toast";
import { buildFileTree, findNodeByPath, type FileNode } from "../lib/file-tree";
import { compareService } from "../service";
import type { SnapshotFile, SnapshotFileContent } from "../types";
import { basenameFromPath, downloadBlob } from "../downloads";
import { CollapsibleSidebar } from "./collapsible-sidebar";
import { DiffViewer } from "./diff-viewer";
import { FileComparison } from "./file-comparison";
import { CompareLabeledSwitch } from "./compare-labeled-switch";
import { FileTree, type FileDiffStatus } from "./file-tree";
import { FileViewer } from "./file-viewer";

interface FileCompareViewProps {
  projectId: string;
  leftFiles: SnapshotFile[];
  rightFiles?: SnapshotFile[];
  leftLabel: string;
  rightLabel?: string;
  leftExperimentId?: string;
  rightExperimentId?: string;
  leftSnapshotId?: string;
  rightSnapshotId?: string;
  leftSnapshotMissing?: boolean;
  rightSnapshotMissing?: boolean;
}

type CompareMode = "split" | "diff" | "side-by-side";

interface DisplayedFileContent {
  path: string;
  extension?: string;
  content: string;
}

function useSnapshotFileContentQuery({
  projectId,
  file,
  allowFetch,
}: {
  projectId: string;
  file: SnapshotFile | null;
  allowFetch: boolean;
}) {
  return useQuery({
    queryKey: [
      QUERY_KEYS.COMPARE.SNAPSHOT_FILE_CONTENT(projectId, file?.path, file?.hash),
    ],
    queryFn: () => {
      if (!file) {
        throw new Error("Snapshot file selection is incomplete");
      }
      return compareService.getSnapshotFileContent(projectId, file);
    },
    enabled: Boolean(file && allowFetch),
    placeholderData: keepPreviousData,
  });
}

export function FileCompareView({
  projectId,
  leftFiles,
  rightFiles,
  leftLabel,
  rightLabel,
  leftExperimentId,
  rightExperimentId,
  leftSnapshotId,
  rightSnapshotId,
  leftSnapshotMissing = false,
  rightSnapshotMissing = false,
}: FileCompareViewProps) {
  const { toast } = useToast();
  const [leftSelectedFile, setLeftSelectedFile] = useState<FileNode | null>(null);
  const [rightSelectedFile, setRightSelectedFile] = useState<FileNode | null>(null);
  const [mode, setMode] = useState<CompareMode>("side-by-side");
  const [autoSelectMatchingFile, setAutoSelectMatchingFile] = useState(true);
  const [showOnlyDifferentFiles, setShowOnlyDifferentFiles] = useState(true);
  const [largeFetchKeys, setLargeFetchKeys] = useState<Set<string>>(() => new Set());
  const hasRightSide = Boolean(rightExperimentId || rightFiles);
  const hasRightSnapshot = Boolean(rightSnapshotId && rightFiles && !rightSnapshotMissing);
  const leftMissingLabel = hasRightSide
    ? "Left experiment has no logged snapshot."
    : "This experiment has no logged snapshot.";

  const differentPaths = useMemo(() => {
    if (!rightFiles) {
      return new Set<string>();
    }

    const paths = new Set<string>();
    const leftByPath = new Map(leftFiles.map((file) => [file.path, file.hash]));
    const rightByPath = new Map(rightFiles.map((file) => [file.path, file.hash]));

    leftByPath.forEach((leftHash, path) => {
      if (rightByPath.get(path) !== leftHash) {
        paths.add(path);
      }
    });
    rightByPath.forEach((rightHash, path) => {
      if (leftByPath.get(path) !== rightHash) {
        paths.add(path);
      }
    });

    return paths;
  }, [leftFiles, rightFiles]);

  const diffStatusBySide = useMemo(() => {
    const left = new Map<string, FileDiffStatus>();
    const right = new Map<string, FileDiffStatus>();

    if (!rightFiles) {
      return { left, right };
    }

    const leftByPath = new Map(leftFiles.map((file) => [file.path, file.hash]));
    const rightByPath = new Map(rightFiles.map((file) => [file.path, file.hash]));

    leftByPath.forEach((leftHash, path) => {
      if (!rightByPath.has(path)) {
        left.set(path, "removed");
      } else if (rightByPath.get(path) !== leftHash) {
        left.set(path, "modified");
      }
    });

    rightByPath.forEach((rightHash, path) => {
      if (!leftByPath.has(path)) {
        right.set(path, "new");
      } else if (leftByPath.get(path) !== rightHash) {
        right.set(path, "modified");
      }
    });

    return { left, right };
  }, [leftFiles, rightFiles]);

  const visibleLeftFiles = useMemo(() => {
    if (!showOnlyDifferentFiles || !rightFiles) {
      return leftFiles;
    }
    return leftFiles.filter((file) => differentPaths.has(file.path));
  }, [differentPaths, leftFiles, rightFiles, showOnlyDifferentFiles]);

  const visibleRightFiles = useMemo(() => {
    if (!rightFiles) {
      return [];
    }
    if (!showOnlyDifferentFiles) {
      return rightFiles;
    }
    return rightFiles.filter((file) => differentPaths.has(file.path));
  }, [differentPaths, rightFiles, showOnlyDifferentFiles]);

  const leftTree = useMemo(
    () => buildFileTree(visibleLeftFiles.map((file) => file.path)),
    [visibleLeftFiles]
  );
  const rightTree = useMemo(
    () => buildFileTree(visibleRightFiles.map((file) => file.path)),
    [visibleRightFiles]
  );

  const visibleLeftSelectedFile =
    leftSelectedFile && findFileInTree(leftTree, leftSelectedFile.path) ? leftSelectedFile : null;
  const visibleRightSelectedFile =
    rightSelectedFile && findFileInTree(rightTree, rightSelectedFile.path)
      ? rightSelectedFile
      : null;
  const activeMode = hasRightSnapshot ? mode : "split";

  const selectedLeftMetadata = visibleLeftSelectedFile
    ? leftFiles.find((file) => file.path === visibleLeftSelectedFile.path) ?? null
    : null;
  const selectedRightMetadata = visibleRightSelectedFile
    ? rightFiles?.find((file) => file.path === visibleRightSelectedFile.path) ?? null
    : null;
  const leftLargeKey = selectedLeftMetadata
    ? largeFetchKey(leftSnapshotId, selectedLeftMetadata)
    : null;
  const rightLargeKey = selectedRightMetadata
    ? largeFetchKey(rightSnapshotId, selectedRightMetadata)
    : null;
  const leftLargeFetchAllowed = Boolean(
    !isLargeSnapshotFile(selectedLeftMetadata) ||
      (leftLargeKey && largeFetchKeys.has(leftLargeKey))
  );
  const rightLargeFetchAllowed = Boolean(
    !isLargeSnapshotFile(selectedRightMetadata) ||
      (rightLargeKey && largeFetchKeys.has(rightLargeKey))
  );

  const leftContentQuery = useSnapshotFileContentQuery({
    projectId,
    file: selectedLeftMetadata,
    allowFetch: leftLargeFetchAllowed,
  });
  const rightContentQuery = useSnapshotFileContentQuery({
    projectId,
    file: selectedRightMetadata,
    allowFetch: rightLargeFetchAllowed,
  });

  const leftContentMatches = fileContentMatches(
    leftContentQuery.data,
    selectedLeftMetadata
  );
  const rightContentMatches = fileContentMatches(
    rightContentQuery.data,
    selectedRightMetadata
  );
  const leftDisplayedContent = toDisplayedFileContent(
    leftContentQuery.data,
    visibleLeftSelectedFile
  );
  const rightDisplayedContent = toDisplayedFileContent(
    rightContentQuery.data,
    visibleRightSelectedFile
  );
  const hasDisplayedComparison = Boolean(leftDisplayedContent && rightDisplayedContent);
  const comparisonIsFetching = leftContentQuery.isFetching || rightContentQuery.isFetching;
  const leftContent = leftContentMatches ? leftContentQuery.data?.content ?? "" : "";
  const rightContent = rightContentMatches ? rightContentQuery.data?.content ?? "" : "";
  const canCompare = Boolean(
    hasRightSnapshot &&
      visibleLeftSelectedFile &&
      visibleRightSelectedFile &&
      leftContentMatches &&
      rightContentMatches
  );

  const allowLargeFetch = (key: string | null) => {
    if (!key) {
      return;
    }
    setLargeFetchKeys((current) => new Set(current).add(key));
  };

  const selectLeftFile = (path: string) => {
    const file = findFileInTree(leftTree, path);
    if (!file) {
      return;
    }

    setLeftSelectedFile(file);

    const matchingRightFile = autoSelectMatchingFile ? findFileInTree(rightTree, path) : null;
    if (matchingRightFile) {
      setRightSelectedFile(matchingRightFile);
    }
  };

  const selectRightFile = (path: string) => {
    const file = findFileInTree(rightTree, path);
    if (!file) {
      return;
    }

    setRightSelectedFile(file);

    const matchingLeftFile = autoSelectMatchingFile ? findFileInTree(leftTree, path) : null;
    if (matchingLeftFile) {
      setLeftSelectedFile(matchingLeftFile);
    }
  };

  const downloadFile = async ({
    files,
    path,
  }: {
    files: SnapshotFile[];
    path: string;
  }) => {
    const file = files.find((item) => item.path === path);
    if (!file) {
      toast({
        title: "Failed to download file",
        description: "File is not present in the loaded snapshot.",
        variant: "destructive",
      });
      return;
    }
    try {
      const blob = await compareService.downloadProjectArtifact(projectId, file.hash);
      downloadBlob(blob, basenameFromPath(file.path));
      toast({ title: "File download started" });
    } catch {
      toast({
        title: "Failed to download file",
        description: "The file could not be downloaded from project storage.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden bg-background">
      <CollapsibleSidebar title={leftLabel} side="left">
        <div className="p-2">
          {leftSnapshotMissing ? (
            <MissingSnapshotWarning label={leftMissingLabel} />
          ) : (
            <FileTree
              data={leftTree}
              selectedFile={visibleLeftSelectedFile?.path}
              onFileSelect={selectLeftFile}
              onFileDownload={(path) =>
                downloadFile({
                  files: leftFiles,
                  path,
                })
              }
              diffStatusByPath={diffStatusBySide.left}
            />
          )}
        </div>
      </CollapsibleSidebar>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b bg-muted/30 px-4 py-2">
          <Tabs value={activeMode} onValueChange={(value) => setMode(value as CompareMode)}>
            <TabsList>
              <TabsTrigger value="side-by-side" disabled={!hasRightSnapshot}>
                Side by Side
              </TabsTrigger>
              <TabsTrigger value="diff" disabled={!canCompare} className="gap-2">
                <GitCompare className="h-3.5 w-3.5" />
                Compare
              </TabsTrigger>
              <TabsTrigger value="split">Split View</TabsTrigger>
            </TabsList>
          </Tabs>

          {hasRightSnapshot && (
            <TooltipProvider delayDuration={250}>
              <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2">
                <CompareLabeledSwitch
                  id="compare-auto-select"
                  checked={autoSelectMatchingFile}
                  onCheckedChange={setAutoSelectMatchingFile}
                  label="Match file"
                  tip="Selecting a file on one side selects the file with the same path on the other side."
                />
                <CompareLabeledSwitch
                  id="compare-different-files"
                  checked={showOnlyDifferentFiles}
                  onCheckedChange={setShowOnlyDifferentFiles}
                  label="Different only"
                  tip="Filters both file trees to files that are added, removed, or modified."
                />
              </div>
            </TooltipProvider>
          )}

          <div className="min-w-0 truncate text-sm text-muted-foreground">
            {visibleLeftSelectedFile?.name ?? "No left file"}
            {hasRightSnapshot && (
              <>
                {canCompare ? " ↔ " : " / "}
                {visibleRightSelectedFile?.name ?? "No right file"}
              </>
            )}
          </div>
        </div>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          {activeMode === "split" ? (
            <>
              <div className={hasRightSide ? "min-w-0 flex-1 border-r" : "min-w-0 flex-1"}>
                {leftSnapshotMissing ? (
                  <MissingSnapshotPane label={leftMissingLabel} />
                ) : visibleLeftSelectedFile || leftDisplayedContent ? (
                  <FileContentPane
                    file={selectedLeftMetadata}
                    displayedContent={leftDisplayedContent}
                    contentLoaded={leftContentMatches}
                    isLoading={leftContentQuery.isFetching}
                    isError={leftContentQuery.isError}
                    largeFetchAllowed={leftLargeFetchAllowed}
                    onFetchLarge={() => allowLargeFetch(leftLargeKey)}
                  />
                ) : (
                  <EmptySelection label="Select a file from the snapshot" />
                )}
              </div>
              {hasRightSide && (
                <div className="min-w-0 flex-1">
                  {rightSnapshotMissing ? (
                    <MissingSnapshotPane label="Right experiment has no logged snapshot." />
                  ) : visibleRightSelectedFile || rightDisplayedContent ? (
                    <FileContentPane
                      file={selectedRightMetadata}
                      displayedContent={rightDisplayedContent}
                      contentLoaded={rightContentMatches}
                      isLoading={rightContentQuery.isFetching}
                      isError={rightContentQuery.isError}
                      largeFetchAllowed={rightLargeFetchAllowed}
                      onFetchLarge={() => allowLargeFetch(rightLargeKey)}
                    />
                  ) : (
                    <EmptySelection label="Select a file from the right snapshot" />
                  )}
                </div>
              )}
            </>
          ) : activeMode === "diff" ? (
            <div className="relative min-w-0 flex-1">
              {canCompare ? (
                <DiffViewer
                  oldContent={leftContent}
                  newContent={rightContent}
                  oldFileName={visibleLeftSelectedFile?.name}
                  newFileName={visibleRightSelectedFile?.name}
                  oldExtension={visibleLeftSelectedFile?.extension}
                  newExtension={visibleRightSelectedFile?.extension}
                />
              ) : leftDisplayedContent && rightDisplayedContent ? (
                <DiffViewer
                  oldContent={leftDisplayedContent.content}
                  newContent={rightDisplayedContent.content}
                  oldFileName={fileNameFromPath(leftDisplayedContent.path)}
                  newFileName={fileNameFromPath(rightDisplayedContent.path)}
                  oldExtension={leftDisplayedContent.extension}
                  newExtension={rightDisplayedContent.extension}
                />
              ) : (
                <EmptySelection label="Select files from both snapshots" />
              )}
              {comparisonIsFetching && hasDisplayedComparison ? <LoadingOverlay /> : null}
            </div>
          ) : (
            <div className="relative min-w-0 flex-1">
              {canCompare && visibleLeftSelectedFile && visibleRightSelectedFile ? (
                <FileComparison
                  leftFile={{
                    path: visibleLeftSelectedFile.path,
                    content: leftContent,
                    extension: visibleLeftSelectedFile.extension,
                  }}
                  rightFile={{
                    path: visibleRightSelectedFile.path,
                    content: rightContent,
                    extension: visibleRightSelectedFile.extension,
                  }}
                />
              ) : leftDisplayedContent && rightDisplayedContent ? (
                <FileComparison
                  leftFile={{
                    path: leftDisplayedContent.path,
                    content: leftDisplayedContent.content,
                    extension: leftDisplayedContent.extension,
                  }}
                  rightFile={{
                    path: rightDisplayedContent.path,
                    content: rightDisplayedContent.content,
                    extension: rightDisplayedContent.extension,
                  }}
                />
              ) : (
                <EmptySelection label="Select files from both snapshots" />
              )}
              {comparisonIsFetching && hasDisplayedComparison ? <LoadingOverlay /> : null}
            </div>
          )}
        </div>
      </div>

      {hasRightSide && (
        <CollapsibleSidebar title={rightLabel ?? "Right"} side="right">
          <div className="p-2">
            {rightSnapshotMissing ? (
              <MissingSnapshotWarning label="Right experiment has no logged snapshot." />
            ) : (
              <FileTree
                data={rightTree}
                selectedFile={visibleRightSelectedFile?.path}
                onFileSelect={selectRightFile}
                onFileDownload={(path) =>
                  downloadFile({
                    files: rightFiles ?? [],
                    path,
                  })
                }
                diffStatusByPath={diffStatusBySide.right}
              />
            )}
          </div>
        </CollapsibleSidebar>
      )}
    </div>
  );
}

function findFileInTree(tree: FileNode[], path: string): FileNode | null {
  const node = findNodeByPath(tree, path);
  return node?.type === "file" ? node : null;
}

function EmptySelection({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      {label}
    </div>
  );
}

function FileContentPane({
  file,
  displayedContent,
  contentLoaded,
  isLoading,
  isError,
  largeFetchAllowed,
  onFetchLarge,
}: {
  file: SnapshotFile | null;
  displayedContent: DisplayedFileContent | null;
  contentLoaded: boolean;
  isLoading: boolean;
  isError: boolean;
  largeFetchAllowed: boolean;
  onFetchLarge: () => void;
}) {
  if (isLargeSnapshotFile(file) && !largeFetchAllowed && !contentLoaded) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="max-w-md rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 shadow-sm dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="min-w-0 space-y-3">
              <div className="font-medium">This file is too large to fetch automatically.</div>
              <div>
                {formatBytes(file?.size ?? 0)} exceeds the{" "}
                {formatBytes(SNAPSHOT_PREVIEW_MAX_BYTES)} preview threshold.
              </div>
              <Button type="button" size="sm" variant="outline" onClick={onFetchLarge}>
                Fetch
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="relative h-full">
        {displayedContent ? (
          <FileViewer
            path={displayedContent.path}
            content={displayedContent.content}
            extension={displayedContent.extension}
          />
        ) : null}
        <LoadingOverlay />
      </div>
    );
  }
  if (isError) {
    return <EmptySelection label="Failed to load file content" />;
  }
  if (!displayedContent) {
    return <EmptySelection label="Select a file from the snapshot" />;
  }
  return (
    <FileViewer
      path={displayedContent.path}
      content={displayedContent.content}
      extension={displayedContent.extension}
    />
  );
}

function LoadingOverlay() {
  return (
    <div
      aria-label="Loading file content"
      className="pointer-events-none absolute right-4 top-4 z-10 rounded-full border bg-background/90 p-2 text-muted-foreground shadow-sm"
    >
      <LoaderCircle className="h-4 w-4 animate-spin" />
    </div>
  );
}

function MissingSnapshotWarning({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-medium text-amber-900 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{label}</span>
      </div>
    </div>
  );
}

function MissingSnapshotPane({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <MissingSnapshotWarning label={label} />
    </div>
  );
}

function isLargeSnapshotFile(file: SnapshotFile | null): boolean {
  return typeof file?.size === "number" && file.size > SNAPSHOT_PREVIEW_MAX_BYTES;
}

function largeFetchKey(snapshotId: string | undefined, file: SnapshotFile): string {
  return `${snapshotId ?? ""}:${file.hash}:${file.path}`;
}

function fileNameFromPath(path: string): string {
  return path.split("/").pop() || path;
}

function fileContentMatches(
  content: SnapshotFileContent | undefined,
  file: SnapshotFile | null
): boolean {
  return Boolean(
    content &&
      file &&
      content.path === file.path &&
      content.hash.toLowerCase() === file.hash.toLowerCase()
  );
}

function toDisplayedFileContent(
  content: SnapshotFileContent | undefined,
  selectedFile: FileNode | null
): DisplayedFileContent | null {
  if (!content) {
    return null;
  }
  return {
    path: content.path,
    extension: content.path === selectedFile?.path ? selectedFile.extension : undefined,
    content: content.content,
  };
}

