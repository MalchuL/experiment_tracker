"use client";

import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

export interface CollapsiblePrefixGroupProps {
  title: string;
  count: number;
  children: ReactNode;
  defaultOpen?: boolean;
}

export function CollapsiblePrefixGroup({
  title,
  count,
  children,
  defaultOpen = true,
}: CollapsiblePrefixGroupProps) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="py-2">
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="group flex w-full items-center justify-between gap-3 border-y border-border px-1 py-2.5 text-left outline-none transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="text-base font-semibold">
            {title} <span className="font-medium text-muted-foreground">({count})</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden px-1 pt-3 pb-1">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}
