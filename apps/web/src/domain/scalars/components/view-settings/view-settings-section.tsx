import type { ReactNode } from "react";

interface ViewSettingsSectionProps {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}

export function ViewSettingsSection({
  title,
  actions,
  children,
  defaultOpen = true,
}: ViewSettingsSectionProps) {
  return (
    <details className="group border-b pb-2" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 py-1.5 text-sm font-medium">
        <span>{title}</span>
        <span className="flex items-center gap-2">
          {actions}
          <span className="text-xs text-muted-foreground group-open:rotate-180">⌄</span>
        </span>
      </summary>
      <div className="min-w-0">{children}</div>
    </details>
  );
}
