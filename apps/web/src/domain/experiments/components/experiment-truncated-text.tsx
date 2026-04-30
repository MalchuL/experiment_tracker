"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { truncateExperimentCardText } from "@/domain/experiments/experiment-card-text";

type ShowTooltip = "auto" | "always";

type ExperimentTruncatedTextProps = {
  text: string;
  className?: string;
  as?: "p" | "span";
  /**
   * "auto": tooltip only when text is shortened by the character limit (table-style).
   * "always": tooltip on every hover with full text; layout uses line-clamp (kanban cards).
   */
  showTooltip?: ShowTooltip;
  /** Used when showTooltip is "always". 1 = single-line ellipsis; 2–4 = multi-line clamp. */
  lineClamp?: 1 | 2 | 3 | 4;
};

function lineClampClass(lines: 1 | 2 | 3 | 4): string {
  if (lines === 1) return "truncate";
  if (lines === 2) return "line-clamp-2";
  if (lines === 3) return "line-clamp-3";
  return "line-clamp-4";
}

export function ExperimentTruncatedText({
  text,
  className,
  as: Comp = "p",
  showTooltip = "auto",
  lineClamp = 2,
}: ExperimentTruncatedTextProps) {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  const always = showTooltip === "always";
  const charSlice = always ? null : truncateExperimentCardText(text);
  const full = always ? text : charSlice!.full;
  const truncated = always ? false : charSlice!.truncated;
  const visible = always ? text : charSlice!.display;

  const line = (
    <Comp
      className={cn(
        "m-0 min-w-0 w-full max-w-full break-words",
        always ? lineClampClass(lineClamp) : "truncate",
        className
      )}
    >
      {visible}
    </Comp>
  );

  const shell = <div className="min-w-0 w-full max-w-full overflow-hidden">{line}</div>;

  if (!always && !truncated) {
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
