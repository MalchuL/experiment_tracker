"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { NavigationMenuLink } from "@/components/ui/navigation-menu";
import { cn } from "@/lib/utils";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";
import type { DocManifestEntry } from "@/lib/docs/docs-manifest";
import {
  buildDocsTopicSections,
  topicSectionContainsPath,
  type DocsTopicSection,
} from "@/lib/docs/docs-manifest";

/**
 * Shared styles for topic links in the Topics aside and Documentation dropdown.
 */
function topicLinkClass(active: boolean): string {
  return cn(
    "rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
    active && "bg-accent font-medium text-accent-foreground",
  );
}

export type DocsTopicNavVariant = "aside" | "menu";

/**
 * Maps `window.location` to the manifest `path` string when the user is under `/docs/*`.
 *
 * @returns e.g. `reference/doc-features`, or `null` on `/docs` or outside `/docs`
 */
export function docsPathFromPathname(pathname: string | null): string | null {
  if (!pathname || pathname === "/docs") return null;
  if (pathname.startsWith("/docs/")) return pathname.slice("/docs/".length);
  return null;
}

export type DocsTopicNavItemsProps = {
  currentPath: string | null;
  variant?: DocsTopicNavVariant;
  /** Prefix for `data-testid` on links (e.g. `docs-nav` vs `nav-docs`). */
  testIdPrefix?: string;
};

/**
 * Renders the full topic tree from `buildDocsTopicSections()`—either flat links (aside)
 * or list-item wrapped links (header `NavigationMenu`).
 */
export function DocsTopicNavItems({
  currentPath,
  variant = "aside",
  testIdPrefix = "docs-nav",
}: DocsTopicNavItemsProps) {
  const sections = buildDocsTopicSections();

  return (
    <>
      {sections.map((section) =>
        section.type === "leaf" ? (
          <TopicLeaf
            key={section.entry.path}
            entry={section.entry}
            currentPath={currentPath}
            testIdPrefix={testIdPrefix}
            variant={variant}
          />
        ) : (
          <TopicGroup
            key={section.segment}
            section={section}
            currentPath={currentPath}
            testIdPrefix={testIdPrefix}
            variant={variant}
          />
        ),
      )}
    </>
  );
}

function TopicLeaf(props: {
  entry: DocManifestEntry;
  currentPath: string | null;
  testIdPrefix: string;
  variant: DocsTopicNavVariant;
}) {
  const { entry, currentPath, testIdPrefix, variant } = props;
  const active = currentPath === entry.path;
  const link = (
    <Link
      href={FRONTEND_ROUTES.DOCS_DOC(entry.path)}
      className={topicLinkClass(active)}
      data-testid={`${testIdPrefix}-${entry.path.replace(/\//g, "-")}`}
    >
      {entry.title}
    </Link>
  );

  if (variant === "menu") {
    return (
      <li>
        <NavigationMenuLink asChild>{link}</NavigationMenuLink>
      </li>
    );
  }

  return link;
}

function TopicGroup(props: {
  section: Extract<DocsTopicSection, { type: "group" }>;
  currentPath: string | null;
  testIdPrefix: string;
  variant: DocsTopicNavVariant;
}) {
  const { section, currentPath, testIdPrefix, variant } = props;
  const defaultOpen = topicSectionContainsPath(section, currentPath);
  const sectionActive = topicSectionContainsPath(section, currentPath);

  const indexAndNested = (
    <div className="min-w-0 flex-1">
      {section.indexEntry ? (
        <TopicGroupIndexLink
          entry={section.indexEntry}
          currentPath={currentPath}
          testIdPrefix={testIdPrefix}
          variant={variant}
        />
      ) : (
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className={cn(
              topicLinkClass(sectionActive),
              "block w-full text-left",
              !sectionActive && "text-muted-foreground",
            )}
            data-testid={`${testIdPrefix}-group-${section.segment}`}
          >
            {section.label}
          </button>
        </CollapsibleTrigger>
      )}
      <CollapsibleContent className="overflow-hidden">
        <TopicChildList variant={variant}>
          {section.children.map((child) => (
            <TopicChildLink
              key={child.path}
              entry={child}
              currentPath={currentPath}
              testIdPrefix={testIdPrefix}
              variant={variant}
            />
          ))}
        </TopicChildList>
      </CollapsibleContent>
    </div>
  );

  // `key` remounts the Collapsible when `currentPath` changes so `defaultOpen` matches the active section.
  const collapsible = (
    <Collapsible
      key={`${section.segment}-${currentPath ?? ""}`}
      defaultOpen={defaultOpen}
      className="min-w-0"
    >
      <div className="flex min-w-0 items-start gap-0.5">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className={cn(
              "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "data-[state=open]:[&>svg]:rotate-90",
            )}
            aria-label={`Toggle ${section.label} section`}
            data-testid={`${testIdPrefix}-toggle-${section.segment}`}
          >
            <ChevronRight className="h-4 w-4 shrink-0 transition-transform duration-200" />
          </button>
        </CollapsibleTrigger>
        {indexAndNested}
      </div>
    </Collapsible>
  );

  if (variant === "menu") {
    return <li className="min-w-0">{collapsible}</li>;
  }

  return collapsible;
}

function TopicGroupIndexLink(props: {
  entry: DocManifestEntry;
  currentPath: string | null;
  testIdPrefix: string;
  variant: DocsTopicNavVariant;
}) {
  const { entry, currentPath, testIdPrefix, variant } = props;
  const active = currentPath === entry.path;
  const link = (
    <Link
      href={FRONTEND_ROUTES.DOCS_DOC(entry.path)}
      className={cn(topicLinkClass(active), "block w-full text-left")}
      data-testid={`${testIdPrefix}-${entry.path.replace(/\//g, "-")}`}
    >
      {entry.title}
    </Link>
  );

  if (variant === "menu") {
    return <NavigationMenuLink asChild>{link}</NavigationMenuLink>;
  }

  return link;
}

function TopicChildList(props: { variant: DocsTopicNavVariant; children: ReactNode }) {
  const { variant, children } = props;
  const bodyClass = "mt-0.5 flex flex-col gap-0.5 py-0.5 pl-3";

  if (variant === "menu") {
    return <ul className={bodyClass}>{children}</ul>;
  }

  return <div className={bodyClass}>{children}</div>;
}

function TopicChildLink(props: {
  entry: DocManifestEntry;
  currentPath: string | null;
  testIdPrefix: string;
  variant: DocsTopicNavVariant;
}) {
  const { entry, currentPath, testIdPrefix, variant } = props;
  const active = currentPath === entry.path;
  const link = (
    <Link
      href={FRONTEND_ROUTES.DOCS_DOC(entry.path)}
      className={topicLinkClass(active)}
      data-testid={`${testIdPrefix}-${entry.path.replace(/\//g, "-")}`}
    >
      {entry.title}
    </Link>
  );

  if (variant === "menu") {
    return (
      <li>
        <NavigationMenuLink asChild>{link}</NavigationMenuLink>
      </li>
    );
  }

  return link;
}

/**
 * Convenience hook: manifest doc path for the current URL under `/docs`.
 */
export function useDocsTopicPath(): string | null {
  return docsPathFromPathname(usePathname());
}
