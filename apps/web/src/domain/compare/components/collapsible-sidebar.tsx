"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface CollapsibleSidebarProps {
  side: "left" | "right";
  title: string;
  children: React.ReactNode;
  defaultCollapsed?: boolean;
  className?: string;
  headerAction?: React.ReactNode;
}

export function CollapsibleSidebar({
  side,
  title,
  children,
  defaultCollapsed = false,
  className,
  headerAction,
}: CollapsibleSidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

  return (
    <div
      className={cn(
        "relative flex border-border bg-background transition-all duration-300",
        side === "left" ? "border-r" : "border-l",
        isCollapsed ? "w-0" : "w-64 md:w-72",
        className
      )}
    >
      <div className={cn("flex flex-1 flex-col overflow-hidden", isCollapsed && "invisible")}>
        <div className="flex items-center gap-2 border-b bg-muted/30 px-4 py-3">
          <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">{title}</h2>
          {headerAction}
        </div>
        <ScrollArea className="flex-1">{children}</ScrollArea>
      </div>

      <div className={cn("absolute top-3 z-10", side === "left" ? "-right-3" : "-left-3")}>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-6 w-6 rounded-full bg-background shadow-md transition-shadow hover:shadow-lg"
          onClick={() => setIsCollapsed((value) => !value)}
          aria-label={isCollapsed ? `Show ${title}` : `Hide ${title}`}
        >
          {side === "left" ? (
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
