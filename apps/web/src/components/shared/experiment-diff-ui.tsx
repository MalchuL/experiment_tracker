import type { ReactNode } from "react";
import { CircleMinus, CirclePlus, PencilLine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ExperimentDiffStatus = "unchanged" | "added" | "removed" | "changed";

export function ExperimentDiffCountBadge({
  status,
  label,
  value,
  compact = false,
}: {
  status: Exclude<ExperimentDiffStatus, "unchanged">;
  label: string;
  value: number;
  compact?: boolean;
}) {
  const marker = status === "added" ? "+" : status === "removed" ? "-" : "~";
  return (
    <Badge variant="outline" className={cn("text-[11px]", experimentDiffBadgeClass(status))}>
      {compact ? `${marker}${value}` : `${label} ${value}`}
    </Badge>
  );
}

export function ExperimentDiffIcon({
  status,
  title,
}: {
  status: ExperimentDiffStatus;
  title?: string;
}) {
  const iconClassName = "h-3.5 w-3.5";
  let icon: ReactNode = null;
  if (status === "added") {
    icon = <CirclePlus className={cn(iconClassName, "text-green-700 dark:text-green-300")} />;
  } else if (status === "removed") {
    icon = <CircleMinus className={cn(iconClassName, "text-red-700 dark:text-red-300")} />;
  } else if (status === "changed") {
    icon = <PencilLine className={cn(iconClassName, "text-amber-700 dark:text-amber-300")} />;
  }
  return icon ? (
    <span title={title} aria-label={title} role={title ? "img" : undefined}>
      {icon}
    </span>
  ) : null;
}

export function experimentDiffSurfaceClass(status: ExperimentDiffStatus): string {
  if (status === "added") return "bg-green-500/10 text-green-800 dark:text-green-300";
  if (status === "removed") return "bg-red-500/10 text-red-800 dark:text-red-300";
  if (status === "changed") return "bg-amber-500/10 text-amber-800 dark:text-amber-300";
  return "text-foreground/80";
}

function experimentDiffBadgeClass(status: Exclude<ExperimentDiffStatus, "unchanged">): string {
  if (status === "added") return "border-green-500/20 bg-green-500/10 text-green-700";
  if (status === "removed") return "border-red-500/20 bg-red-500/10 text-red-700";
  return "border-amber-500/20 bg-amber-500/10 text-amber-700";
}
