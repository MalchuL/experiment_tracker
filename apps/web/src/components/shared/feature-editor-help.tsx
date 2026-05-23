"use client";

import { CircleHelp } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const FEATURE_EDITOR_HELP_CONTENT = (
  <div className="space-y-2 text-xs leading-relaxed">
    <p className="font-medium">Nested bullet list</p>
    <ul className="list-disc space-y-1 pl-4">
      <li>
        <span className="font-medium">Tab</span> — indent (nest under the line above)
      </li>
      <li>
        <span className="font-medium">Shift+Tab</span> — outdent (move up one level)
      </li>
    </ul>
    <p className="text-muted-foreground">
      Copy and paste use two leading spaces per nesting level (tabs count as one level).
    </p>
  </div>
);

type FeatureEditorHelpProps = {
  label: string;
  className?: string;
};

export function FeatureEditorLabelWithHelp({ label, className }: FeatureEditorHelpProps) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      {label}
      <FeatureEditorHelpIcon />
    </span>
  );
}

export function FeatureEditorHelpIcon() {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex shrink-0 rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label="Feature editor help"
        >
          <CircleHelp className="h-3.5 w-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs p-3">
        {FEATURE_EDITOR_HELP_CONTENT}
      </TooltipContent>
    </Tooltip>
  );
}
