/**
 * Single source of truth for which markdown files are published under `/docs/*`
 * and how they appear in navigation and the `/docs` index.
 *
 * Each `path` maps to `apps/web/content/docs/{path}.md` (nested folders allowed).
 */
import type { CSSProperties } from "react";

export type DocManifestEntry = {
  path: string;
  title: string;
  description?: string;
};

export const DOCS_MANIFEST: DocManifestEntry[] = [
  {
    path: "architecture-overview",
    title: "Architecture overview",
    description: "How the web app, API, scalars service, and object storage fit together.",
  },
  {
    path: "contributing/adding-pages",
    title: "Adding documentation pages",
    description: "Checklist for authors and coding agents: manifest, files, routes, images.",
  },
  {
    path: "contributing/extending-doc-pipeline",
    title: "Extending the docs pipeline",
    description: "For developers: remark/rehype, directives, sanitize, and React markdown components.",
  },
  {
    path: "examples/common-patterns",
    title: "Common documentation patterns",
    description: "Recipes: warnings, collapsibles, and structure for onboarding and runbooks.",
  },
  {
    path: "getting-started",
    title: "Getting started",
    description: "Use the workspace, projects, and where to find help in the UI.",
  },
  {
    path: "getting-started/file-descriptors",
    title: "File descriptors & local services",
    description:
      "Too many open files, FD limits, uvicorn --reload, and backend/scalars code paths to check.",
  },
  {
    path: "getting-started/workspace",
    title: "Workspace & navigation",
    description: "Sidebar, header, and moving between projects, teams, and docs.",
  },
  {
    path: "getting-started/projects",
    title: "Projects",
    description: "Creating projects, the project dashboard, and where settings live.",
  },
  {
    path: "reference/dag-view",
    title: "DAG view: metrics on nodes",
    description:
      "Experiment lineage graph: how many metrics appear per node and which constant controls the cap.",
  },
  {
    path: "reference/doc-features",
    title: "Callouts, details & formatting",
    description: "Live examples: warning, tip, danger, note, info, caution, and collapsible blocks.",
  },
  {
    path: "reference/metric-display-formatting",
    title: "Metric display: precision & thresholds",
    description:
      "Tune mathjs auto-format (significant digits, exponent band) and comparison epsilon for tables, DAG, and sidebars.",
  },
];

/** Joins URL segments into the manifest `path` key (`foo/bar`). */
function pathKey(segments: string[]): string {
  return segments.join("/");
}

/**
 * Looks up a manifest row for the current doc route segments
 * (e.g. `['getting-started','workspace']` → `getting-started/workspace`).
 */
export function getDocManifestEntry(segments: string[]): DocManifestEntry | undefined {
  if (segments.length === 0) return undefined;
  const key = pathKey(segments);
  return DOCS_MANIFEST.find((d) => d.path === key);
}

/**
 * Static paths for `docs/[...path]/page.tsx`. Each `path` array is one manifest URL split on `/`.
 */
export function getStaticDocPathParams(): { path: string[] }[] {
  return DOCS_MANIFEST.map((d) => ({
    path: d.path.split("/").filter(Boolean),
  }));
}

/**
 * Nesting depth of a manifest path: `a` → 0, `a/b` → 1, `a/b/c` → 2.
 * Used for index-card inset and future layout tweaks.
 */
export function docPathDepth(path: string): number {
  return path.split("/").filter(Boolean).length - 1;
}

/** Either a single top-level doc link or a folder group (shared first URL segment). */
export type DocsTopicSection =
  | { type: "leaf"; entry: DocManifestEntry }
  | {
      type: "group";
      segment: string;
      /** Shown when there is no page at exactly `{segment}` (e.g. only `contributing/foo` exists). */
      label: string;
      indexEntry?: DocManifestEntry;
      children: DocManifestEntry[];
    };

/** Turns `getting-started` → `Getting Started` for group headings without an index page. */
function humanizePathSegment(segment: string): string {
  return segment
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Builds the Topics sidebar / header menu: standalone pages are leaves; paths that share a
 * first segment (`getting-started`, `getting-started/x`) become one collapsible group.
 */
export function buildDocsTopicSections(): DocsTopicSection[] {
  const entries = [...DOCS_MANIFEST].sort((a, b) => a.path.localeCompare(b.path));
  const byFirstSegment = new Map<string, DocManifestEntry[]>();

  for (const e of entries) {
    const first = e.path.split("/")[0]!;
    const group = byFirstSegment.get(first) ?? [];
    group.push(e);
    byFirstSegment.set(first, group);
  }

  const sections: DocsTopicSection[] = [];

  for (const [firstSegment, group] of [...byFirstSegment.entries()].sort((a, b) =>
    a[0].localeCompare(b[0]),
  )) {
    const indexEntry = group.find((e) => e.path === firstSegment);
    const nestedOnly = group.filter((e) => e.path.startsWith(`${firstSegment}/`));

    if (nestedOnly.length === 0) {
      sections.push({ type: "leaf", entry: group[0]! });
      continue;
    }

    sections.push({
      type: "group",
      segment: firstSegment,
      label: humanizePathSegment(firstSegment),
      indexEntry,
      children: nestedOnly,
    });
  }

  return sections;
}

/**
 * Whether the active doc URL belongs to this section (for default-open collapsibles).
 */
export function topicSectionContainsPath(section: DocsTopicSection, currentPath: string | null): boolean {
  if (currentPath === null) return false;
  if (section.type === "leaf") return section.entry.path === currentPath;
  return (
    section.indexEntry?.path === currentPath ||
    section.children.some((c) => c.path === currentPath)
  );
}

const DOC_INDEX_NESTED_PAD_BASE_REM = 2;
const DOC_INDEX_NESTED_PAD_STEP_REM = 0.5;
const DOC_INDEX_NESTED_PAD_RIGHT_REM = 1.5;

/**
 * Inline styles for `/docs` index cards when `path` is nested (`foo/bar` → extra left padding).
 * Formula: `paddingLeft = base + (depth - 1) * step` (rem).
 */
export function docIndexEntryPaddingStyle(
  path: string,
): Pick<CSSProperties, "paddingLeft" | "paddingRight"> | undefined {
  const depth = docPathDepth(path);
  if (depth <= 0) return undefined;
  const paddingLeftRem = DOC_INDEX_NESTED_PAD_BASE_REM + (depth - 1) * DOC_INDEX_NESTED_PAD_STEP_REM;
  return {
    paddingLeft: `${paddingLeftRem}rem`,
    paddingRight: `${DOC_INDEX_NESTED_PAD_RIGHT_REM}rem`,
  };
}
