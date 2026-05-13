import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export type RightSidebarVariant = "overlay" | "push";

interface RightSidebarShellProps {
  title: ReactNode;
  children: ReactNode;
  onClose?: () => void;
  headerPrefix?: ReactNode;
  headerActions?: ReactNode;
  widthClassName?: string;
  /** overlay = fixed over content (e.g. DAG); push = flex sibling — main column shrinks (list/kanban). */
  variant?: RightSidebarVariant;
  className?: string;
  testId?: string;
}

export function RightSidebarShell({
  title,
  children,
  onClose,
  headerPrefix,
  headerActions,
  widthClassName = "w-96",
  variant = "overlay",
  className,
  testId,
}: RightSidebarShellProps) {
  const isPush = variant === "push";

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col bg-background border-l",
        isPush
          ? "h-full w-full shrink-0 self-stretch shadow-sm md:max-w-[400px] md:w-[400px]"
          : cn("fixed inset-y-0 right-0 z-50 shadow-lg", widthClassName),
        className
      )}
      data-testid={testId}
    >
      <div className="flex shrink-0 items-center justify-between border-b p-4">
        <div className="flex min-w-0 items-center gap-2">
          {headerPrefix}
          <h2 className="truncate font-semibold">{title}</h2>
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          {onClose ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              data-testid="button-close-sidebar"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
