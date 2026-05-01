'use client';

import * as React from 'react';
import { ChevronRight, File, Folder, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FileNode, FileTreeData } from '@/lib/file-tree';
import { getFileIconColor } from '@/lib/file-tree';

interface FileTreeProps {
  data: FileTreeData;
  selectedFile?: string | null;
  onFileSelect?: (path: string) => void;
  className?: string;
}

interface TreeNodeProps {
  node: FileNode;
  level: number;
  selectedFile?: string | null;
  onFileSelect?: (path: string) => void;
  expandedDirs: Set<string>;
  onToggleDir: (path: string) => void;
}

function TreeNode({
  node,
  level,
  selectedFile,
  onFileSelect,
  expandedDirs,
  onToggleDir,
}: TreeNodeProps) {
  const isExpanded = expandedDirs.has(node.path);
  const isSelected = selectedFile === node.path;
  const isDirectory = node.type === 'directory';

  const handleClick = () => {
    if (isDirectory) {
      onToggleDir(node.path);
    } else {
      onFileSelect?.(node.path);
    }
  };

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1.5 px-2 py-1.5 cursor-pointer rounded-md hover:bg-accent/50 transition-colors group text-sm',
          isSelected && 'bg-accent text-accent-foreground font-medium',
          !isSelected && 'text-foreground/90'
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        {isDirectory ? (
          <>
            <ChevronRight
              className={cn(
                'h-4 w-4 shrink-0 transition-transform text-muted-foreground',
                isExpanded && 'rotate-90'
              )}
            />
            {isExpanded ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-blue-500" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-blue-500" />
            )}
          </>
        ) : (
          <>
            <div className="w-4" />
            <File
              className={cn(
                'h-4 w-4 shrink-0',
                getFileIconColor(node.extension)
              )}
            />
          </>
        )}
        <span className="truncate flex-1">{node.name}</span>
      </div>
      {isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedFile={selectedFile}
              onFileSelect={onFileSelect}
              expandedDirs={expandedDirs}
              onToggleDir={onToggleDir}
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
}: FileTreeProps) {
  const [expandedDirs, setExpandedDirs] = React.useState<Set<string>>(
    new Set()
  );

  const handleToggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  // Auto-expand directories in the path of selected file
  React.useEffect(() => {
    if (selectedFile) {
      const parts = selectedFile.split('/').filter(Boolean);
      const newExpanded = new Set(expandedDirs);
      let currentPath = '';

      // Expand all parent directories
      for (let i = 0; i < parts.length - 1; i++) {
        currentPath += '/' + parts[i];
        newExpanded.add(currentPath);
      }

      setExpandedDirs(newExpanded);
    }
  }, [selectedFile]);

  return (
    <div className={cn('py-2', className)}>
      {data.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          level={0}
          selectedFile={selectedFile}
          onFileSelect={onFileSelect}
          expandedDirs={expandedDirs}
          onToggleDir={handleToggleDir}
        />
      ))}
    </div>
  );
}
