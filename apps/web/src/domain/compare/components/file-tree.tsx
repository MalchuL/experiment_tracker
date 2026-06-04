"use client";

import { useMemo, useState } from "react";
import {
  ChevronRight,
  CircleDot,
  Copy,
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
import { getFileIconColor } from "../lib/file-tree";

export type FileDiffStatus = "modified" | "new" | "removed";

interface FileTreeProps {
  data: FileTreeData;
  selectedFile?: string | null;
  onFileSelect?: (path: string) => void;
  className?: string;
  diffStatusByPath?: Map<string, FileDiffStatus>;
}

function TreeNode({
  node,
  level,
  selectedFile,
  onFileSelect,
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
  diffStatusByPath?: Map<string, FileDiffStatus>;
  collapsedPaths: Set<string>;
  onToggleDirectory: (path: string) => void;
  onExpandDirectory: (path: string) => void;
  onCollapseDirectory: (path: string) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onCopyPath: (path: string) => void;
}) {
  const isSelected = selectedFile === node.path;
  const isDirectory = node.type === "directory";
  const isCollapsed = isDirectory && collapsedPaths.has(node.path);
  const diffStatus = isDirectory ? undefined : diffStatusByPath?.get(node.path);
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
      {diffStatus && <FileDiffStatusIcon status={diffStatus} />}
    </button>
  );

  return (
    <div>
      <ContextMenu>
        <ContextMenuTrigger asChild>{row}</ContextMenuTrigger>
        <ContextMenuContent>
          {isDirectory ? (
            <>
              <ContextMenuItem onSelect={() => onExpandDirectory(node.path)}>
                Expand folder
              </ContextMenuItem>
              <ContextMenuItem onSelect={() => onCollapseDirectory(node.path)}>
                Collapse folder
              </ContextMenuItem>
            </>
          ) : (
            <ContextMenuItem onSelect={() => onFileSelect?.(node.path)}>
              Open file
            </ContextMenuItem>
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
  className,
  diffStatusByPath,
}: FileTreeProps) {
  const { toast } = useToast();
  const [collapsedPaths, setCollapsedPaths] = useState<Set<string>>(new Set());
  const directoryPaths = useMemo(() => collectDirectoryPaths(data), [data]);

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
              onExpandDirectory={(path) =>
                setCollapsedPaths((current) => {
                  const next = new Set(current);
                  next.delete(path);
                  return next;
                })
              }
              onCollapseDirectory={(path) =>
                setCollapsedPaths((current) => new Set(current).add(path))
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

function collectDirectoryPaths(data: FileTreeData): string[] {
  const paths: string[] = [];
  const visit = (nodes: FileNode[]) => {
    for (const node of nodes) {
      if (node.type === "directory") {
        paths.push(node.path);
        if (node.children) {
          visit(node.children);
        }
      }
    }
  };
  visit(data);
  return paths;
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
