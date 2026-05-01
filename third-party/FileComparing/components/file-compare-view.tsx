'use client';

import { useState } from 'react';
import { FileNode, buildFileTree, findNodeByPath } from '@/lib/file-tree';
import { FileTree } from '@/components/file-tree';
import { CodeViewer } from '@/components/code-viewer';
import { DiffViewer } from '@/components/diff-viewer';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, GitCompare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

function findFileInTree(tree: FileNode[], path: string): FileNode | null {
  return findNodeByPath(tree, path);
}

interface FileCompareViewProps {
  leftFiles: Array<{ path: string; content: string }>;
  rightFiles: Array<{ path: string; content: string }>;
  leftLabel?: string;
  rightLabel?: string;
}

export function FileCompareView({
  leftFiles,
  rightFiles,
  leftLabel = 'Left',
  rightLabel = 'Right',
}: FileCompareViewProps) {
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [leftSelectedFile, setLeftSelectedFile] = useState<FileNode | null>(null);
  const [rightSelectedFile, setRightSelectedFile] = useState<FileNode | null>(null);
  const [mode, setMode] = useState<'split' | 'diff'>('split');

  const leftTree = buildFileTree(leftFiles.map((f) => f.path));
  const rightTree = buildFileTree(rightFiles.map((f) => f.path));

  const getFileContent = (path: string, files: Array<{ path: string; content: string }>) => {
    return files.find((f) => f.path === path)?.content || '';
  };

  const leftContent = leftSelectedFile
    ? getFileContent(leftSelectedFile.path, leftFiles)
    : '';
  const rightContent = rightSelectedFile
    ? getFileContent(rightSelectedFile.path, rightFiles)
    : '';

  const canCompare = leftSelectedFile && rightSelectedFile;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Left Sidebar */}
      <div
        className={cn(
          'flex flex-col border-r bg-muted/30 transition-all duration-300',
          leftCollapsed ? 'w-0' : 'w-64'
        )}
      >
        {!leftCollapsed && (
          <>
            <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="size-2 rounded-full bg-green-500" />
                <span className="font-medium text-sm">{leftLabel}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLeftCollapsed(true)}
                className="size-7"
              >
                <ChevronLeft className="size-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-auto p-2">
              <FileTree
                data={leftTree}
                selectedFile={leftSelectedFile?.path}
                onFileSelect={(path) => {
                  const file = leftTree.find(node => node.path === path) || 
                    findFileInTree(leftTree, path);
                  if (file?.type === 'file') {
                    setLeftSelectedFile(file);
                  }
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Left Collapsed Toggle */}
      {leftCollapsed && (
        <div className="flex items-center border-r bg-muted/30">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setLeftCollapsed(false)}
            className="size-8 rounded-none"
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
          <Tabs value={mode} onValueChange={(v) => setMode(v as 'split' | 'diff')}>
            <TabsList>
              <TabsTrigger value="split" className="gap-2">
                Split View
              </TabsTrigger>
              <TabsTrigger value="diff" className="gap-2" disabled={!canCompare}>
                <GitCompare className="size-3.5" />
                Compare
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {leftSelectedFile && (
              <span className="truncate max-w-xs">{leftSelectedFile.name}</span>
            )}
            {canCompare && <span>↔</span>}
            {rightSelectedFile && (
              <span className="truncate max-w-xs">{rightSelectedFile.name}</span>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex flex-1 overflow-hidden">
          {mode === 'split' ? (
            <>
              {/* Left Content */}
              <div className="flex-1 border-r overflow-hidden">
                {leftSelectedFile ? (
                  <CodeViewer
                    fileName={leftSelectedFile.name}
                    content={leftContent}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    <p>Select a file from the left sidebar</p>
                  </div>
                )}
              </div>

              {/* Right Content */}
              <div className="flex-1 overflow-hidden">
                {rightSelectedFile ? (
                  <CodeViewer
                    fileName={rightSelectedFile.name}
                    content={rightContent}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    <p>Select a file from the right sidebar</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 overflow-hidden">
              {canCompare ? (
                <DiffViewer
                  oldContent={leftContent}
                  newContent={rightContent}
                  oldFileName={leftSelectedFile?.name}
                  newFileName={rightSelectedFile?.name}
                />
              ) : (
                <div className="flex h-full items-center justify-center text-muted-foreground">
                  <p>Select files from both sidebars to compare</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Collapsed Toggle */}
      {rightCollapsed && (
        <div className="flex items-center border-l bg-muted/30">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setRightCollapsed(false)}
            className="size-8 rounded-none"
          >
            <ChevronLeft className="size-4" />
          </Button>
        </div>
      )}

      {/* Right Sidebar */}
      <div
        className={cn(
          'flex flex-col border-l bg-muted/30 transition-all duration-300',
          rightCollapsed ? 'w-0' : 'w-64'
        )}
      >
        {!rightCollapsed && (
          <>
            <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setRightCollapsed(true)}
                className="size-7"
              >
                <ChevronRight className="size-4" />
              </Button>
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{rightLabel}</span>
                <div className="size-2 rounded-full bg-blue-500" />
              </div>
            </div>
            <div className="flex-1 overflow-auto p-2">
              <FileTree
                data={rightTree}
                selectedFile={rightSelectedFile?.path}
                onFileSelect={(path) => {
                  const file = rightTree.find(node => node.path === path) || 
                    findFileInTree(rightTree, path);
                  if (file?.type === 'file') {
                    setRightSelectedFile(file);
                  }
                }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
