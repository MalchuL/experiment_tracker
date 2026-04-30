"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { BookOpen, List } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { cn } from "@/lib/utils";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import type { DocTocItem } from "@/lib/docs/extract-doc-toc";
import { DocsTopicNavItems } from "@/components/docs/docs-topic-links";

type DocsPageShellProps = {
  /**
   * If set, renders `PageHeader` (docs index only). Article routes omit this so `#` in markdown
   * is the single visible title—manifest `title`/`description` stay for nav and cards only.
   */
  title?: string;
  description?: string;
  /** Active manifest path (`getting-started/workspace`), or `null` on `/docs`. */
  currentPath: string | null;
  toc: DocTocItem[];
  children: ReactNode;
};

/** Shared layout for sticky side rails (topics + in-page TOC): width, scroll, card chrome. */
const DOCS_ASIDE_PANEL_CLASS = cn(
  "w-full shrink-0 lg:w-[13.5rem] lg:shrink-0",
  "lg:sticky lg:top-3 lg:self-start lg:max-h-[calc(100dvh-4.5rem)] lg:overflow-y-auto",
  "rounded-lg border border-border bg-card/40 p-3 lg:rounded-md",
);

/** Main article column: horizontal + top padding so body is not flush to Topics/TOC or header. */
const DOCS_MAIN_COLUMN_CLASS =
  "order-2 min-w-0 flex-1 px-4 pt-4 sm:px-6 sm:pt-5 lg:px-8 lg:pt-6 lg:order-none";

/**
 * Docs layout: Topics (left), main column (center), optional “On this page” TOC (right).
 * On small screens columns stack; side rails match width and sticky behavior on `lg+`.
 */
export function DocsPageShell({
  title,
  description,
  currentPath,
  toc,
  children,
}: DocsPageShellProps) {
  const hasToc = toc.length > 0;

  return (
    <div
      className={cn(
        "flex w-full min-h-[calc(100dvh-5.5rem)] min-w-0 max-w-none flex-col gap-6 pb-10 lg:flex-row lg:items-start lg:gap-3",
        /* Outer inset: align with workspace chrome; slightly tighter left near app sidebar */
        "pl-2 pr-2 sm:pl-3 sm:pr-3 md:pl-2 md:pr-4 lg:pl-2 lg:pr-3",
      )}
    >
      <DocsTopicsAside currentPath={currentPath} />

      <div className={DOCS_MAIN_COLUMN_CLASS}>
        {title ? (
          <div className="mb-6 space-y-4">
            <PageHeader title={title} description={description} />
          </div>
        ) : null}
        {children}
      </div>

      {hasToc ? <DocsTocAside toc={toc} /> : null}
    </div>
  );
}

function DocsTopicsAside({ currentPath }: { currentPath: string | null }) {
  return (
    <aside
      className={cn("order-1 lg:order-none", DOCS_ASIDE_PANEL_CLASS)}
      aria-label="Documentation topics"
      data-testid="docs-topics-aside"
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <BookOpen className="h-4 w-4 shrink-0" />
        Topics
      </div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">All topics</p>
      <nav className="flex flex-col gap-1.5">
        <Link
          href={FRONTEND_ROUTES.DOCS}
          className={cn(
            "rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
            currentPath === null && "bg-accent font-medium text-accent-foreground",
          )}
          data-testid="docs-nav-index"
        >
          Overview
        </Link>
        <DocsTopicNavItems currentPath={currentPath} variant="aside" testIdPrefix="docs-nav" />
      </nav>
    </aside>
  );
}

function DocsTocAside({ toc }: { toc: DocTocItem[] }) {
  return (
    <aside
      className={cn("order-3 lg:order-none", DOCS_ASIDE_PANEL_CLASS)}
      aria-label="On this page"
      data-testid="docs-toc-aside"
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <List className="h-4 w-4 shrink-0" />
        On this page
      </div>
      <nav className="flex flex-col gap-0.5 border-l border-border pl-2.5">
        {toc.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className={cn(
              "block rounded-r-md py-1.5 pr-2 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground",
              item.level === 1 && "pl-0 font-medium text-foreground/90",
              item.level === 2 && "pl-3",
              item.level === 3 && "pl-6 text-xs",
            )}
            data-testid={`docs-toc-${item.id}`}
          >
            {item.text}
          </a>
        ))}
      </nav>
    </aside>
  );
}
