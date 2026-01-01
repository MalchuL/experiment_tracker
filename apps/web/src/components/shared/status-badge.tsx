import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExperimentStatusType, HypothesisStatusType } from "@shared/schema";

interface StatusBadgeProps {
  status: ExperimentStatusType | HypothesisStatusType;
  size?: "sm" | "default";
}

const experimentStatusConfig: Record<string, { label: string; className: string }> = {
  planned: {
    label: "Planned",
    className: "bg-muted text-muted-foreground",
  },
  running: {
    label: "Running",
    className: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  },
  complete: {
    label: "Complete",
    className: "bg-green-500/15 text-green-600 dark:text-green-400",
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/15 text-red-600 dark:text-red-400",
  },
};

const hypothesisStatusConfig: Record<string, { label: string; className: string }> = {
  proposed: {
    label: "Proposed",
    className: "bg-muted text-muted-foreground",
  },
  testing: {
    label: "Testing",
    className: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400",
  },
  supported: {
    label: "Supported",
    className: "bg-green-500/15 text-green-600 dark:text-green-400",
  },
  refuted: {
    label: "Refuted",
    className: "bg-red-500/15 text-red-600 dark:text-red-400",
  },
  inconclusive: {
    label: "Inconclusive",
    className: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  },
};

export function StatusBadge({ status, size = "default" }: StatusBadgeProps) {
  const config = experimentStatusConfig[status] || hypothesisStatusConfig[status];
  
  if (!config) {
    return <Badge variant="secondary">{status}</Badge>;
  }

  return (
    <Badge 
      className={cn(
        "font-medium border-0",
        config.className,
        size === "sm" && "text-xs px-2 py-0.5"
      )}
      data-testid={`badge-status-${status}`}
    >
      {config.label}
    </Badge>
  );
}
