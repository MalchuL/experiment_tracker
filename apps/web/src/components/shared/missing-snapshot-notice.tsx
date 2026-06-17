import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface MissingSnapshotNoticeProps {
  label?: string;
  className?: string;
}

export function MissingSnapshotNotice({
  label = "This experiment has no logged snapshot.",
  className,
}: MissingSnapshotNoticeProps) {
  return (
    <div
      className={cn(
        "rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-medium text-amber-900 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-200",
        className
      )}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{label}</span>
      </div>
    </div>
  );
}
