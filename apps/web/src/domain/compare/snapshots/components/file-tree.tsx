"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronRight,
  CircleDot,
  Copy,
  Download,
  File,
  Folder,
  FolderOpen,
  Minus,
  Plus,
} from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { FileNode, FileTreeData } from "../lib/file-tree";
import {
  collectDirectoryPaths,
  collectDirectoryPathsInSubtree,
  getFileIconColor,
} from "../lib/file-tree";

export type FileDiffStatus = "modified" | "new" | "removed";

interface FileTreeProps {
  data: FileTreeData;
  selectedFile?: string | null;
  onFileSelect?: (path: string) => void;
  onFileDownload?: (path: string) => void;
  className?: string;
  diffStatusByPath?: Map<string, FileDiffStatus>;
}

function TreeNode({
  node,
  level,
  selectedFile,
  onFileSelect,
  onFileDownload,
  diffStatusByPath,
  collapsedPaths,
  onToggleDirectory,
  onExpandDirectory,
  onCollapseDirectory,
  onExpandAll,
  onCollapseAll,
  onCopyPath,
}: {
  node: FileNode;
  level: number;
  selectedFile?: string | null;
  onFileSelect?: (path: string) => void;
  onFileDownload?: (path: string) => void;
  diffStatusByPath?: Map<string, FileDiffStatus>;
  collapsedPaths: Set<string>;
  onToggleDirectory: (path: string) => void;
  onExpandDirectory: (node: FileNode) => void;
  onCollapseDirectory: (node: FileNode) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onCopyPath: (path: string) => void;
}) {
  const isSelected = selectedFile === node.path;
  const isDirectory = node.type === "directory";
  const isCollapsed = isDirectory && collapsedPaths.has(node.path);
  const hasDirectoryDiff = isDirectory && directoryContainsDiffFiles(node, diffStatusByPath);
  const fileDiffStatus = isDirectory ? undefined : diffStatusByPath?.get(node.path);
  const row = (
    <button
      type="button"
      className={cn(
        "flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent/50",
        isSelected && "bg-accent font-medium text-accent-foreground",
        !isSelected && "text-foreground/90"
      )}
      style={{ paddingLeft: `${level * 12 + 8}px` }}
      onClick={() => {
        if (isDirectory) {
          onToggleDirectory(node.path);
          return;
        }
        onFileSelect?.(node.path);
      }}
    >
      {isDirectory ? (
        <>
          <ChevronRight
            className={cn(
              "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
              !isCollapsed && "rotate-90"
            )}
          />
          {isCollapsed ? (
            <Folder className="h-4 w-4 shrink-0 text-blue-500" />
          ) : (
            <FolderOpen className="h-4 w-4 shrink-0 text-blue-500" />
          )}
        </>
      ) : (
        <>
          <div className="w-4 shrink-0" />
          <File className={cn("h-4 w-4 shrink-0", getFileIconColor(node.extension))} />
        </>
      )}
      <span className="min-w-0 flex-1 truncate">{node.name}</span>
      {hasDirectoryDiff ? <FolderDiffIndicator /> : null}
      {fileDiffStatus ? <FileDiffStatusIcon status={fileDiffStatus} /> : null}
    </button>
  );

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger asChild>{row}</ContextMenuTrigger>
        <ContextMenuContent>
          {isDirectory ? (
            <>
              <ContextMenuItem onSelect={() => onExpandDirectory(node)}>
                Expand folder
              </ContextMenuItem>
              <ContextMenuItem onSelect={() => onCollapseDirectory(node)}>
                Collapse folder
              </ContextMenuItem>
            </>
          ) : (
            <>
              <ContextMenuItem onSelect={() => onFileSelect?.(node.path)}>
                Open file
              </ContextMenuItem>
              {onFileDownload ? (
                <ContextMenuItem onSelect={() => onFileDownload(node.path)}>
                  <Download className="mr-2 h-3.5 w-3.5" />
                  Download file
                </ContextMenuItem>
              ) : null}
            </>
          )}
          <ContextMenuItem onSelect={() => onCopyPath(node.path)}>
            <Copy className="mr-2 h-3.5 w-3.5" />
            Copy path
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem onSelect={onExpandAll}>Expand all</ContextMenuItem>
          <ContextMenuItem onSelect={onCollapseAll}>Collapse all</ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
      {isDirectory && node.children && !isCollapsed && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedFile={selectedFile}
              onFileSelect={onFileSelect}
              onFileDownload={onFileDownload}
              diffStatusByPath={diffStatusByPath}
              collapsedPaths={collapsedPaths}
              onToggleDirectory={onToggleDirectory}
              onExpandDirectory={onExpandDirectory}
              onCollapseDirectory={onCollapseDirectory}
              onExpandAll={onExpandAll}
              onCollapseAll={onCollapseAll}
              onCopyPath={onCopyPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({
  data,
  selectedFile,
  onFileSelect,
  onFileDownload,
  className,
  diffStatusByPath,
}: FileTreeProps) {
  const { toast } = useToast();
  const directoryPaths = useMemo(() => collectDirectoryPaths(data), [data]);
  const [collapsedPaths, setCollapsedPaths] = useState<Set<string>>(() =>
    new Set(collectDirectoryPaths(data))
  );
  const previousDirectoryPathsRef = useRef<string[]>(collectDirectoryPaths(data));

  useEffect(() => {
    const previousPaths = new Set(previousDirectoryPathsRef.current);
    const addedDirectoryPaths = directoryPaths.filter((path) => !previousPaths.has(path));
    previousDirectoryPathsRef.current = directoryPaths;

    if (addedDirectoryPaths.length === 0) {
      return;
    }

    const overlapCount = directoryPaths.filter((path) => previousPaths.has(path)).length;
    const isMostlyNewTree =
      previousPaths.size > 0 && overlapCount / Math.max(directoryPaths.length, 1) < 0.5;

    if (isMostlyNewTree) {
      return;
    }

    setCollapsedPaths((current) => {
      const next = new Set(current);
      for (const path of addedDirectoryPaths) {
        next.add(path);
      }
      return next;
    });
  }, [directoryPaths]);

  const copyPath = async (path: string) => {
    try {
      await navigator.clipboard.writeText(path);
      toast({ title: "Path copied" });
    } catch {
      toast({ title: "Failed to copy path", variant: "destructive" });
    }
  };

  const expandAll = () => setCollapsedPaths(new Set());
  const collapseAll = () => setCollapsedPaths(new Set(directoryPaths));

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div className={cn("min-h-full py-2", className)}>
          {data.map((node) => (
            <TreeNode
              key={node.path}
              node={node}
              level={0}
              selectedFile={selectedFile}
              onFileSelect={onFileSelect}
              onFileDownload={onFileDownload}
              diffStatusByPath={diffStatusByPath}
              collapsedPaths={collapsedPaths}
              onToggleDirectory={(path) =>
                setCollapsedPaths((current) => {
                  const next = new Set(current);
                  if (next.has(path)) {
                    next.delete(path);
                  } else {
                    next.add(path);
                  }
                  return next;
                })
              }
              onExpandDirectory={(folderNode) =>
                setCollapsedPaths((current) => {
                  const next = new Set(current);
                  for (const path of collectDirectoryPathsInSubtree(folderNode)) {
                    next.delete(path);
                  }
                  return next;
                })
              }
              onCollapseDirectory={(folderNode) =>
                setCollapsedPaths((current) => {
                  const next = new Set(current);
                  for (const path of collectDirectoryPathsInSubtree(folderNode)) {
                    next.add(path);
                  }
                  return next;
                })
              }
              onExpandAll={expandAll}
              onCollapseAll={collapseAll}
              onCopyPath={copyPath}
            />
          ))}
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onSelect={expandAll}>Expand all</ContextMenuItem>
        <ContextMenuItem onSelect={collapseAll}>Collapse all</ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function directoryContainsDiffFiles(
  node: FileNode,
  diffStatusByPath?: Map<string, FileDiffStatus>
): boolean {
  if (!diffStatusByPath || node.type !== "directory") {
    return false;
  }

  const visit = (current: FileNode): boolean => {
    if (current.type === "file") {
      return diffStatusByPath.has(current.path);
    }
    return current.children?.some(visit) ?? false;
  };

  return visit(node);
}

function FolderDiffIndicator() {
  return (
    <span
      className="h-2 w-2 shrink-0 rounded-full bg-blue-500"
      aria-label="Folder contains changed files"
    />
  );
}

function FileDiffStatusIcon({ status }: { status: FileDiffStatus }) {
  if (status === "new") {
    return <Plus className="h-3.5 w-3.5 shrink-0 text-green-600" aria-label="New file" />;
  }
  if (status === "removed") {
    return <Minus className="h-3.5 w-3.5 shrink-0 text-red-600" aria-label="Removed file" />;
  }
  return <CircleDot className="h-3.5 w-3.5 shrink-0 text-yellow-600" aria-label="Modified file" />;
}
