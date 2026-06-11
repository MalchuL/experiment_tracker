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
   * `card`: character cap + optional Radix tooltip (kanban, compact cards).
   * `table`: full string in the DOM with CSS ellipsis / line-clamp + native `title` (copy/select gets full text).
   */
  variant?: "card" | "table";
  /**
   * Card only. "auto": tooltip only when text is shortened by the character limit.
   * "always": tooltip on every hover; layout uses line-clamp (kanban cards).
   */
  showTooltip?: ShowTooltip;
  /** Card + showTooltip "always". 1 = single-line ellipsis; 2–4 = multi-line clamp. */
  lineClamp?: 1 | 2 | 3 | 4;
  /**
   * Table variant only: `single` = one-line ellipsis (`truncate`); `multi` = up to two lines
   * (`line-clamp-2`) for descriptions.
   */
  tableClamp?: "single" | "multi";
  /** Table variant only: wrap onto multiple lines instead of truncating. */
  tableWrap?: boolean;
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
  variant = "card",
  showTooltip = "auto",
  lineClamp = 2,
  tableClamp = "single",
  tableWrap = false,
}: ExperimentTruncatedTextProps) {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  if (variant === "table") {
    return (
      <Comp
        title={trimmed}
        className={cn(
          "m-0 min-w-0 w-full max-w-full",
          tableWrap
            ? "whitespace-normal break-words"
            : tableClamp === "multi"
              ? "line-clamp-2 break-words"
              : "truncate",
          className
        )}
      >
        {trimmed}
      </Comp>
    );
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
