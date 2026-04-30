"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { truncateExperimentCardText } from "@/domain/experiments/experiment-card-text";

type ExperimentTruncatedTextProps = {
  text: string;
  className?: string;
  as?: "p" | "span";
};

/** Truncates per `truncateExperimentCardText`; hover shows full text when truncated. */
export function ExperimentTruncatedText({
  text,
  className,
  as: Comp = "p",
}: ExperimentTruncatedTextProps) {
  const { display, full, truncated } = truncateExperimentCardText(text);

  const line = (
    <Comp className={cn("m-0 min-w-0 w-full max-w-full truncate", className)}>{display}</Comp>
  );

  const shell = <div className="min-w-0 w-full max-w-full overflow-hidden">{line}</div>;

  if (!truncated) {
    return shell;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{shell}</TooltipTrigger>
      <TooltipContent side="top" className="max-w-md">
        <p className="m-0 whitespace-pre-wrap break-words text-sm">{full}</p>
      </TooltipContent>
    </Tooltip>
  );
}
