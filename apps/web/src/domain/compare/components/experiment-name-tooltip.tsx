import type { ReactNode } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ExperimentNameTooltip({
  name,
  children,
}: {
  name: string;
  children: ReactNode;
}) {
  return (
    <TooltipProvider delayDuration={250}>
      <Tooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side="top" className="max-w-none whitespace-normal">
          {name}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
