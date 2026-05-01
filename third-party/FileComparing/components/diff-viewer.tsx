'use client';

import { computeDiff, getDiffStats, DiffLine } from '@/lib/diff';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface DiffViewerProps {
  oldContent: string;
  newContent: string;
  oldFileName?: string;
  newFileName?: string;
  className?: string;
}

export function DiffViewer({
  oldContent,
  newContent,
  oldFileName = 'Original',
  newFileName = 'Modified',
  className,
}: DiffViewerProps) {
  const diff = computeDiff(oldContent, newContent);
  const stats = getDiffStats(diff);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium text-foreground/90">Comparing:</span>
          <span className="text-muted-foreground">{oldFileName}</span>
          <span className="text-muted-foreground">↔</span>
          <span className="text-muted-foreground">{newFileName}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
            +{stats.additions}
          </Badge>
          <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/20">
            -{stats.deletions}
          </Badge>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="min-w-max">
          <div className="font-mono text-sm">
            {diff.map((line, index) => (
              <DiffLineComponent key={index} line={line} />
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

function DiffLineComponent({ line }: { line: DiffLine }) {
  const bgColor = {
    add: 'bg-green-500/10 hover:bg-green-500/15',
    remove: 'bg-red-500/10 hover:bg-red-500/15',
    unchanged: 'hover:bg-accent/30',
  }[line.type];

  const textColor = {
    add: 'text-foreground/90',
    remove: 'text-foreground/90',
    unchanged: 'text-foreground/80',
  }[line.type];

  const lineIndicator = {
    add: '+',
    remove: '-',
    unchanged: ' ',
  }[line.type];

  const indicatorColor = {
    add: 'text-green-600',
    remove: 'text-red-600',
    unchanged: 'text-transparent',
  }[line.type];

  return (
    <div className={cn('flex gap-3 px-4 py-0.5 transition-colors', bgColor)}>
      <div className="flex gap-3 select-none shrink-0">
        <span className="text-muted-foreground/50 text-right w-8">
          {line.lineNumber.old || ''}
        </span>
        <span className="text-muted-foreground/50 text-right w-8">
          {line.lineNumber.new || ''}
        </span>
        <span className={cn('w-4', indicatorColor)}>{lineIndicator}</span>
      </div>
      <code className={cn('flex-1', textColor)}>
        {line.content || ' '}
      </code>
    </div>
  );
}
