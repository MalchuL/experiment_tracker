'use client';

import { getLanguageFromExtension } from '@/lib/file-tree';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CodeViewerProps {
  fileName: string;
  content: string;
  className?: string;
  highlightLines?: number[];
}

export function CodeViewer({ fileName, content, className, highlightLines = [] }: CodeViewerProps) {
  const extension = fileName.split('.').pop();
  const language = getLanguageFromExtension(extension);
  const lines = content.split('\n');

  return (
    <ScrollArea className={cn('h-full w-full', className)}>
      <div className="min-w-max">
        <pre className="p-4 text-sm font-mono">
          {lines.map((line, index) => (
            <div
              key={index}
              className={cn(
                'flex gap-4',
                highlightLines.includes(index + 1) && 'bg-accent/50'
              )}
            >
              <span className="select-none text-muted-foreground/60 text-right w-8 shrink-0">
                {index + 1}
              </span>
              <code className="flex-1 text-foreground/90">
                {line || ' '}
              </code>
            </div>
          ))}
        </pre>
      </div>
    </ScrollArea>
  );
}
