'use client';

import * as React from 'react';
import { File } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getLanguageFromExtension } from '@/lib/file-tree';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface FileViewerProps {
  path: string;
  content: string;
  extension?: string;
  className?: string;
}

export function FileViewer({
  path,
  content,
  extension,
  className,
}: FileViewerProps) {
  const language = getLanguageFromExtension(extension);
  const lines = content.split('\n');
  const fileName = path.split('/').pop() || path;

  return (
    <Card className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b bg-muted/30">
        <File className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium truncate">{fileName}</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {lines.length} lines
        </span>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="font-mono text-sm">
          {lines.map((line, index) => (
            <div
              key={index}
              className="flex hover:bg-accent/30 transition-colors"
            >
              <div className="sticky left-0 select-none text-right text-muted-foreground/60 bg-muted/20 px-4 py-1 min-w-[3.5rem] border-r">
                {index + 1}
              </div>
              <div className="px-4 py-1 flex-1">
                <pre className="whitespace-pre-wrap break-words">{line || ' '}</pre>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
