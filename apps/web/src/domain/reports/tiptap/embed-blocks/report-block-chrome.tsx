"use client";

import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export interface ReportBlockChromeProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  selected?: boolean;
  children?: React.ReactNode;
}

/** Shared card frame for every embed block (Tiptap node view or standalone preview). */
export function ReportBlockChrome({
  icon: Icon,
  title,
  description,
  selected,
  children,
}: ReportBlockChromeProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card text-card-foreground shadow-sm transition-colors",
        selected ? "border-primary ring-1 ring-primary/30" : "border-border",
      )}
      data-report-embed="true"
    >
      <div className="flex items-start gap-3 border-b border-border px-3 py-2">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium leading-tight">{title}</div>
          {description ? (
            <div className="mt-0.5 text-xs text-muted-foreground">{description}</div>
          ) : null}
        </div>
      </div>
      {children ? <div className="space-y-3 px-3 py-3">{children}</div> : null}
    </div>
  );
}
