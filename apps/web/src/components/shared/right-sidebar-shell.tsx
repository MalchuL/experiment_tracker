import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

interface RightSidebarShellProps {
  title: ReactNode;
  children: ReactNode;
  onClose?: () => void;
  headerPrefix?: ReactNode;
  headerActions?: ReactNode;
  widthClassName?: string;
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
  className,
  testId,
}: RightSidebarShellProps) {
  return (
    <div
      className={`fixed right-0 top-0 h-full ${widthClassName} bg-background border-l z-50 flex flex-col shadow-lg ${className ?? ""}`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2 min-w-0">
          {headerPrefix}
          <h2 className="font-semibold truncate">{title}</h2>
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              data-testid="button-close-sidebar"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
