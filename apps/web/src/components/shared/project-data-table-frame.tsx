"use client";

import { createContext, useContext, useMemo, useCallback, type ReactNode, type Ref } from "react";
import { cn } from "@/lib/utils";

export type ProjectDataTableFrameContextValue = {
  /** When true, the first `leadColumnCount` columns use horizontal sticky positioning inside the scrollport. */
  pinLeadColumns: boolean;
  /** How many leading columns participate in horizontal pin (grip+experiment = 2; metrics experiment-only = 1). */
  leadColumnCount: number;
};

const ProjectDataTableFrameContext = createContext<ProjectDataTableFrameContextValue | null>(null);

export function useProjectDataTableFrame(): ProjectDataTableFrameContextValue {
  const v = useContext(ProjectDataTableFrameContext);
  return v ?? { pinLeadColumns: true, leadColumnCount: 2 };
}

export type ProjectDataTableFrameProps = {
  pinLeadColumns: boolean;
  leadColumnCount?: number;
  toolbar?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Merged with the internal scroll container ref (e.g. infinite-scroll `IntersectionObserver` root). */
  scrollContainerRef?: Ref<HTMLDivElement>;
};

/**
 * Shared scroll shell: one `overflow-auto` viewport for vertical and horizontal scrolling,
 * optional context for pinned lead columns (implemented by table components).
 */
export function ProjectDataTableFrame({
  pinLeadColumns,
  leadColumnCount = 2,
  toolbar,
  footer,
  children,
  className,
  scrollContainerRef,
}: ProjectDataTableFrameProps) {
  const ctx = useMemo(
    () => ({ pinLeadColumns, leadColumnCount }),
    [pinLeadColumns, leadColumnCount]
  );

  const setScrollRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (typeof scrollContainerRef === "function") {
        scrollContainerRef(node);
      } else if (scrollContainerRef && typeof scrollContainerRef === "object" && "current" in scrollContainerRef) {
        (scrollContainerRef as { current: HTMLDivElement | null }).current = node;
      }
    },
    [scrollContainerRef]
  );

  return (
    <div
      className={cn(
        "flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-border bg-card",
        className
      )}
    >
      {toolbar ? <div className="shrink-0 border-b border-border px-3 py-2">{toolbar}</div> : null}
      <ProjectDataTableFrameContext.Provider value={ctx}>
        <div ref={setScrollRef} className="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto">
          {children}
        </div>
      </ProjectDataTableFrameContext.Provider>
      {footer ? <div className="shrink-0 border-t border-border">{footer}</div> : null}
    </div>
  );
}
