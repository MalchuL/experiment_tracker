"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GitCompare } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { buildFileTree, findNodeByPath, type FileNode } from "../lib/file-tree";
import { compareService } from "../service";
import type { SnapshotFile } from "../types";
import { CollapsibleSidebar } from "./collapsible-sidebar";
import { DiffViewer } from "./diff-viewer";
import { FileComparison } from "./file-comparison";
import { FileTree, type FileDiffStatus } from "./file-tree";
import { FileViewer } from "./file-viewer";

interface FileCompareViewProps {
  leftFiles: SnapshotFile[];
  rightFiles?: SnapshotFile[];
  leftLabel: string;
  rightLabel?: string;
  leftExperimentId?: string;
  rightExperimentId?: string;
  leftSnapshotId?: string;
  rightSnapshotId?: string;
}

type CompareMode = "split" | "diff" | "side-by-side";

function useSnapshotFileContentQuery({
  experimentId,
  snapshotId,
  file,
}: {
  experimentId?: string;
  snapshotId?: string;
  file: SnapshotFile | null;
}) {
  return useQuery({
    queryKey: [
      QUERY_KEYS.COMPARE.SNAPSHOT_FILE_CONTENT(
        experimentId,
        snapshotId,
        file?.path,
        file?.hash
      ),
    ],
    queryFn: () => {
      if (!experimentId || !file) {
        throw new Error("Snapshot file selection is incomplete");
      }
      return compareService.getSnapshotFileContent(experimentId, {
        path: file.path,
        hash: file.hash,
      });
    },
    enabled: Boolean(experimentId && snapshotId && file),
  });
}

export function FileCompareView({
  leftFiles,
  rightFiles,
  leftLabel,
  rightLabel,
  leftExperimentId,
  rightExperimentId,
  leftSnapshotId,
  rightSnapshotId,
}: FileCompareViewProps) {
  const [leftSelectedFile, setLeftSelectedFile] = useState<FileNode | null>(null);
  const [rightSelectedFile, setRightSelectedFile] = useState<FileNode | null>(null);
  const [mode, setMode] = useState<CompareMode>("side-by-side");
  const [autoSelectMatchingFile, setAutoSelectMatchingFile] = useState(true);
  const [showOnlyDifferentFiles, setShowOnlyDifferentFiles] = useState(true);
  const hasRightSnapshot = Boolean(rightFiles);

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

  const leftContentQuery = useSnapshotFileContentQuery({
    experimentId: leftExperimentId,
    snapshotId: leftSnapshotId,
    file: selectedLeftMetadata,
  });
  const rightContentQuery = useSnapshotFileContentQuery({
    experimentId: rightExperimentId,
    snapshotId: rightSnapshotId,
    file: selectedRightMetadata,
  });

  const leftContent = leftContentQuery.data?.content ?? "";
  const rightContent = rightContentQuery.data?.content ?? "";
  const canCompare = Boolean(
    hasRightSnapshot &&
      visibleLeftSelectedFile &&
      visibleRightSelectedFile &&
      leftContentQuery.data &&
      rightContentQuery.data
  );

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

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden bg-background">
      <CollapsibleSidebar title={leftLabel} side="left">
        <div className="p-2">
          <FileTree
            data={leftTree}
            selectedFile={visibleLeftSelectedFile?.path}
            onFileSelect={selectLeftFile}
            diffStatusByPath={diffStatusBySide.left}
          />
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
              <div className="flex shrink-0 items-center gap-4 text-sm">
                <CheckboxControl
                  id="compare-auto-select"
                  checked={autoSelectMatchingFile}
                  onCheckedChange={setAutoSelectMatchingFile}
                  label="Match file"
                  tip="Selecting a file on one side selects the file with the same path on the other side."
                />
                <CheckboxControl
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
              <div className={hasRightSnapshot ? "min-w-0 flex-1 border-r" : "min-w-0 flex-1"}>
                {visibleLeftSelectedFile ? (
                  <FileContentPane
                    path={visibleLeftSelectedFile.path}
                    extension={visibleLeftSelectedFile.extension}
                    content={leftContent}
                    isLoading={leftContentQuery.isLoading}
                    isError={leftContentQuery.isError}
                  />
                ) : (
                  <EmptySelection label="Select a file from the snapshot" />
                )}
              </div>
              {hasRightSnapshot && (
                <div className="min-w-0 flex-1">
                  {visibleRightSelectedFile ? (
                    <FileContentPane
                      path={visibleRightSelectedFile.path}
                      extension={visibleRightSelectedFile.extension}
                      content={rightContent}
                      isLoading={rightContentQuery.isLoading}
                      isError={rightContentQuery.isError}
                    />
                  ) : (
                    <EmptySelection label="Select a file from the right snapshot" />
                  )}
                </div>
              )}
            </>
          ) : activeMode === "diff" ? (
            <div className="min-w-0 flex-1">
              {canCompare ? (
                <DiffViewer
                  oldContent={leftContent}
                  newContent={rightContent}
                  oldFileName={visibleLeftSelectedFile?.name}
                  newFileName={visibleRightSelectedFile?.name}
                  oldExtension={visibleLeftSelectedFile?.extension}
                  newExtension={visibleRightSelectedFile?.extension}
                />
              ) : visibleLeftSelectedFile && visibleRightSelectedFile ? (
                <EmptySelection label="Loading selected files..." />
              ) : (
                <EmptySelection label="Select files from both snapshots" />
              )}
            </div>
          ) : (
            <div className="min-w-0 flex-1">
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
              ) : visibleLeftSelectedFile && visibleRightSelectedFile ? (
                <EmptySelection label="Loading selected files..." />
              ) : (
                <EmptySelection label="Select files from both snapshots" />
              )}
            </div>
          )}
        </div>
      </div>

      {hasRightSnapshot && (
        <CollapsibleSidebar title={rightLabel ?? "Right"} side="right">
          <div className="p-2">
            <FileTree
              data={rightTree}
              selectedFile={visibleRightSelectedFile?.path}
              onFileSelect={selectRightFile}
              diffStatusByPath={diffStatusBySide.right}
            />
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
  path,
  extension,
  content,
  isLoading,
  isError,
}: {
  path: string;
  extension?: string;
  content: string;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading) {
    return <EmptySelection label="Loading file..." />;
  }
  if (isError) {
    return <EmptySelection label="Failed to load file content" />;
  }
  return <FileViewer path={path} content={content} extension={extension} />;
}

function CheckboxControl({
  id,
  checked,
  onCheckedChange,
  label,
  tip,
}: {
  id: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  tip: string;
}) {
  const control = (
    <label
      htmlFor={id}
      className="flex cursor-pointer select-none items-center gap-2 text-muted-foreground"
    >
      <Checkbox
        id={id}
        checked={checked}
        onCheckedChange={(value) => onCheckedChange(value === true)}
      />
      <span>{label}</span>
    </label>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{control}</TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        {tip}
      </TooltipContent>
    </Tooltip>
  );
}
