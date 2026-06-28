import type { CSSProperties, ReactNode } from "react";
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
  style?: CSSProperties;
  onResizePointerDown?: (event: React.PointerEvent<HTMLButtonElement>) => void;
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
  style,
  onResizePointerDown,
  testId,
}: RightSidebarShellProps) {
  const isPush = variant === "push";

  return (
    <div
      className={cn(
        "relative flex min-h-0 flex-col bg-background border-l",
        isPush
          ? "h-full w-full shrink-0 self-stretch shadow-sm md:max-w-[400px] md:w-[400px]"
          : cn("fixed inset-y-0 right-0 z-50 shadow-lg", widthClassName),
        className
      )}
      style={style}
      data-testid={testId}
    >
      {onResizePointerDown ? (
        <button
          type="button"
          aria-label="Resize sidebar"
          className="absolute left-0 top-0 z-10 h-full w-1 cursor-ew-resize bg-transparent transition-colors hover:bg-primary/30"
          onPointerDown={onResizePointerDown}
        />
      ) : null}
      <div className="flex shrink-0 items-start justify-between gap-2 border-b p-4">
        <div className="flex min-w-0 flex-1 items-start gap-2">
          {headerPrefix}
          <h2 className="min-w-0 flex-1 whitespace-normal break-words font-semibold">
            {title}
          </h2>
        </div>
        <div className="flex shrink-0 items-center gap-2">
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
