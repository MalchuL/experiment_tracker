'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CollapsibleSidebarProps {
  side: 'left' | 'right';
  title: string;
  children: React.ReactNode;
  defaultCollapsed?: boolean;
  className?: string;
}

export function CollapsibleSidebar({
  side,
  title,
  children,
  defaultCollapsed = false,
  className,
}: CollapsibleSidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

  return (
    <div
      className={cn(
        'relative border-border bg-background transition-all duration-300 flex',
        side === 'left' ? 'border-r' : 'border-l',
        isCollapsed ? 'w-0' : 'w-64 md:w-72',
        className
      )}
    >
      {/* Sidebar Content */}
      <div
        className={cn(
          'flex-1 flex flex-col overflow-hidden',
          isCollapsed && 'invisible'
        )}
      >
        <div className="px-4 py-3 border-b bg-muted/30">
          <h2 className="font-semibold text-sm">{title}</h2>
        </div>
        <ScrollArea className="flex-1">{children}</ScrollArea>
      </div>

      {/* Toggle Button */}
      <div
        className={cn(
          'absolute top-3 z-10',
          side === 'left' ? '-right-3' : '-left-3'
        )}
      >
        <Button
          variant="outline"
          size="icon"
          className="h-6 w-6 rounded-full bg-background shadow-md hover:shadow-lg transition-shadow"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {side === 'left' ? (
            isCollapsed ? (
              <ChevronRight className="h-3 w-3" />
            ) : (
              <ChevronLeft className="h-3 w-3" />
            )
          ) : isCollapsed ? (
            <ChevronLeft className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
        </Button>
      </div>
    </div>
  );
}
