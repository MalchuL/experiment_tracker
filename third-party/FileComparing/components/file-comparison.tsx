'use client';

import * as React from 'react';
import { File, GitCompare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface FileComparisonProps {
  leftFile: {
    path: string;
    content: string;
    extension?: string;
  };
  rightFile: {
    path: string;
    content: string;
    extension?: string;
  };
  className?: string;
}

type DiffLine = {
  type: 'same' | 'added' | 'removed' | 'changed';
  leftLineNumber?: number;
  rightLineNumber?: number;
  leftContent?: string;
  rightContent?: string;
};

function computeSimpleDiff(
  leftLines: string[],
  rightLines: string[]
): DiffLine[] {
  const result: DiffLine[] = [];
  const maxLines = Math.max(leftLines.length, rightLines.length);

  for (let i = 0; i < maxLines; i++) {
    const leftLine = leftLines[i];
    const rightLine = rightLines[i];

    if (leftLine === undefined && rightLine !== undefined) {
      // Added line
      result.push({
        type: 'added',
        rightLineNumber: i + 1,
        rightContent: rightLine,
      });
    } else if (leftLine !== undefined && rightLine === undefined) {
      // Removed line
      result.push({
        type: 'removed',
        leftLineNumber: i + 1,
        leftContent: leftLine,
      });
    } else if (leftLine === rightLine) {
      // Same line
      result.push({
        type: 'same',
        leftLineNumber: i + 1,
        rightLineNumber: i + 1,
        leftContent: leftLine,
        rightContent: rightLine,
      });
    } else {
      // Changed line
      result.push({
        type: 'changed',
        leftLineNumber: i + 1,
        rightLineNumber: i + 1,
        leftContent: leftLine,
        rightContent: rightLine,
      });
    }
  }

  return result;
}

export function FileComparison({
  leftFile,
  rightFile,
  className,
}: FileComparisonProps) {
  const leftLines = leftFile.content.split('\n');
  const rightLines = rightFile.content.split('\n');
  const diff = computeSimpleDiff(leftLines, rightLines);

  const leftFileName = leftFile.path.split('/').pop() || leftFile.path;
  const rightFileName = rightFile.path.split('/').pop() || rightFile.path;

  const stats = {
    added: diff.filter((d) => d.type === 'added').length,
    removed: diff.filter((d) => d.type === 'removed').length,
    changed: diff.filter((d) => d.type === 'changed').length,
  };

  return (
    <Card className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 mb-2">
          <GitCompare className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-semibold">File Comparison</span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {stats.added > 0 && (
            <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
              +{stats.added} added
            </Badge>
          )}
          {stats.removed > 0 && (
            <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/20">
              -{stats.removed} removed
            </Badge>
          )}
          {stats.changed > 0 && (
            <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20">
              ~{stats.changed} changed
            </Badge>
          )}
        </div>
      </div>

      {/* File Names */}
      <div className="grid grid-cols-2 border-b">
        <div className="flex items-center gap-2 px-4 py-2 border-r bg-muted/20">
          <File className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium truncate">{leftFileName}</span>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-muted/20">
          <File className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium truncate">{rightFileName}</span>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="font-mono text-sm">
          {diff.map((line, index) => {
            const bgClass =
              line.type === 'added'
                ? 'bg-green-500/10'
                : line.type === 'removed'
                ? 'bg-red-500/10'
                : line.type === 'changed'
                ? 'bg-yellow-500/10'
                : '';

            return (
              <div
                key={index}
                className={cn('grid grid-cols-2 hover:bg-accent/20', bgClass)}
              >
                {/* Left side */}
                <div className="flex border-r">
                  <div className="sticky left-0 select-none text-right text-muted-foreground/60 bg-muted/20 px-3 py-1 min-w-[3rem] border-r text-xs">
                    {line.leftLineNumber || ''}
                  </div>
                  <div className="px-3 py-1 flex-1">
                    <pre className="whitespace-pre-wrap break-words">
                      {line.leftContent || ' '}
                    </pre>
                  </div>
                </div>

                {/* Right side */}
                <div className="flex">
                  <div className="sticky left-0 select-none text-right text-muted-foreground/60 bg-muted/20 px-3 py-1 min-w-[3rem] border-r text-xs">
                    {line.rightLineNumber || ''}
                  </div>
                  <div className="px-3 py-1 flex-1">
                    <pre className="whitespace-pre-wrap break-words">
                      {line.rightContent || ' '}
                    </pre>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </Card>
  );
}
