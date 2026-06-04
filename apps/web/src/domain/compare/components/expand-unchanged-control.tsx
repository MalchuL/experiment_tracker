"use client";

import { Checkbox } from "@/components/ui/checkbox";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const EXPAND_UNCHANGED_TIP =
  "When on, every line is shown. When off, unchanged regions between edits are collapsed (identical files always show in full).";

interface ExpandUnchangedControlProps {
  id: string;
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  disabled?: boolean;
}

export function ExpandUnchangedControl({
  id,
  expanded,
  onExpandedChange,
  disabled = false,
}: ExpandUnchangedControlProps) {
  return (
    <TooltipProvider delayDuration={250}>
      <Tooltip>
        <TooltipTrigger asChild>
          <label
            htmlFor={id}
            className={
              disabled
                ? "flex cursor-not-allowed select-none items-center gap-2 text-sm text-muted-foreground/60"
                : "flex cursor-pointer select-none items-center gap-2 text-sm text-muted-foreground"
            }
          >
            <Checkbox
              id={id}
              checked={expanded}
              disabled={disabled}
              onCheckedChange={(value) => onExpandedChange(value === true)}
            />
            <span>Expand unchanged</span>
          </label>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          {EXPAND_UNCHANGED_TIP}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
