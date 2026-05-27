"use client";

import type { ComponentType, ReactNode } from "react";
import { createElement } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, type LucideIcon, Info, Lightbulb, OctagonAlert } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkDirective from "remark-directive";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { cn } from "@/lib/utils";
import type { DocTocItem } from "@/lib/docs/extract-doc-toc";
import { remarkDocFeatures } from "@/lib/docs/remark-doc-features";
import { remarkHeadingIds } from "@/lib/docs/remark-heading-ids";
import { docsRehypeSanitizeSchema } from "@/lib/docs/docs-sanitize-schema";

type DocsMarkdownProps = {
  markdown: string;
  className?: string;
  /** When set, `#`–`###` get stable `id`s from `extractDocToc` order for TOC anchors. */
  toc?: DocTocItem[];
};

/** Scroll-margin so in-page `#hash` links clear the sticky workspace header. */
const HEADING_SCROLL_CLASS = "scroll-mt-24";

const CALLOUT_ICON_BOX =
  "mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background/80";

/** Maps `docs-callout-{variant}` class segment to the Lucide icon shown in the gutter. */
const CALLOUT_ICONS: Record<string, LucideIcon> = {
  warning: AlertTriangle,
  caution: AlertTriangle,
  danger: OctagonAlert,
  tip: Lightbulb,
  note: Info,
  info: Info,
};

const DEFAULT_CALLOUT_ICON: LucideIcon = Info;

/**
 * Parses the variant segment from `className` (e.g. `docs-callout-warning` → `warning`).
 */
function calloutVariantFromClassName(className?: string): string | undefined {
  const m = String(className ?? "").match(/(?:^|\s)docs-callout-([\w-]+)(?:\s|$)/);
  return m?.[1];
}

function calloutIconForVariant(variant: string | undefined): LucideIcon {
  if (!variant) return DEFAULT_CALLOUT_ICON;
  return CALLOUT_ICONS[variant] ?? DEFAULT_CALLOUT_ICON;
}

/**
 * Renders directive callouts as an aside with icon + body (styles in `globals.css` `.docs-callout-*`).
 */
function DocsCalloutAside({
  className,
  children,
}: {
  className?: string;
  children?: ReactNode;
}) {
  const variant = calloutVariantFromClassName(className);
  const Icon = calloutIconForVariant(variant);

  return (
    <aside className={cn("docs-callout not-prose", className)}>
      <div className="docs-callout-inner flex gap-3">
        <span className={cn(CALLOUT_ICON_BOX, "docs-callout-icon-ring text-foreground")} aria-hidden>
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1 space-y-2 [&_p]:mb-2 [&_p:last-child]:mb-0">{children}</div>
      </div>
    </aside>
  );
}

const REMARK_PLUGINS = [remarkGfm, remarkDirective, remarkDocFeatures, remarkHeadingIds];

/**
 * Renders markdown with GFM, doc directives (callouts / details), sanitization, and app-specific
 * link/image/callout behavior.
 */
export function DocsMarkdown({ markdown, className, toc }: DocsMarkdownProps) {
  const pathname = usePathname();

  const heading =
    (Tag: "h1" | "h2" | "h3") =>
    ({
      children,
      className: nodeClassName,
      id,
    }: {
      children?: ReactNode;
      className?: string;
      id?: string;
    }) => {
      return createElement(Tag, { id, className: cn(HEADING_SCROLL_CLASS, nodeClassName) }, children);
    };

  const scrollToHashTarget = (href: string): boolean => {
    if (!href.includes("#") || typeof window === "undefined") return false;
    const targetUrl = new URL(href, window.location.href);
    if (targetUrl.origin !== window.location.origin || targetUrl.pathname !== pathname) {
      return false;
    }
    const id = decodeURIComponent(targetUrl.hash.slice(1));
    if (!id) return false;
    const target = document.getElementById(id);
    if (!target) return false;
    window.history.pushState(null, "", `${targetUrl.pathname}${targetUrl.search}${targetUrl.hash}`);
    target.scrollIntoView({ block: "start" });
    return true;
  };

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, docsRehypeSanitizeSchema]]}
        components={{
          h1: heading("h1"),
          h2: heading("h2"),
          h3: heading("h3"),
          a: ({ href, children }): ReactNode => {
            if (href?.startsWith("/")) {
              return (
                <Link
                  href={href}
                  onClick={(event) => {
                    if (scrollToHashTarget(href)) {
                      event.preventDefault();
                    }
                  }}
                >
                  {children as never}
                </Link>
              );
            }
            if (href?.startsWith("#")) {
              return (
                <a
                  href={href}
                  onClick={(event) => {
                    if (scrollToHashTarget(href)) {
                      event.preventDefault();
                    }
                  }}
                >
                  {children as never}
                </a>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children as never}
              </a>
            );
          },
          img: ({ src, alt }): ReactNode => {
            if (!src || typeof src !== "string") return null;
            return (
              <span className="docs-figure block my-6">
                {/* eslint-disable-next-line @next/next/no-img-element -- markdown URLs are dynamic / public paths */}
                <img
                  src={src}
                  alt={alt ?? ""}
                  loading="lazy"
                  decoding="async"
                  className="max-w-full h-auto rounded-md border border-border bg-muted/20 shadow-sm"
                />
              </span>
            );
          },
          aside: DocsCalloutAside,
          details: DetailsWithCollapsibleStyles,
          summary: CollapsibleSummaryRow,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

const DetailsWithCollapsibleStyles: ComponentType<{
  className?: string;
  children?: ReactNode;
}> = ({ className, children, ...props }) => (
  <details className={cn("docs-collapsible group/details my-4", className)} {...props}>
    {children}
  </details>
);

const COLLAPSIBLE_SUMMARY_CLASSES =
  "docs-collapsible-summary flex min-h-11 cursor-pointer list-none items-center gap-3 rounded-md px-5 py-3.5 text-base font-medium leading-snug text-foreground outline-none transition-colors hover:bg-muted/80 sm:min-h-12 sm:py-4 [&::-webkit-details-marker]:hidden";

const COLLAPSIBLE_CHEVRON_CLASSES =
  "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-lg leading-none text-muted-foreground transition-transform group-open/details:rotate-90";

const CollapsibleSummaryRow: ComponentType<{
  className?: string;
  children?: ReactNode;
}> = ({ className, children, ...props }) => (
  <summary className={cn(COLLAPSIBLE_SUMMARY_CLASSES, className)} {...props}>
    <span className={COLLAPSIBLE_CHEVRON_CLASSES} aria-hidden>
      ›
    </span>
    <span className="flex-1">{children}</span>
  </summary>
);
