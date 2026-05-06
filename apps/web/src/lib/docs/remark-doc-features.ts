import type { Root } from "mdast";
import type { ContainerDirective } from "mdast-util-directive";
import { visit } from "unist-util-visit";

/** Directive names that render as styled callouts (`:::warning` … `:::`). */
const CALLOUT_NAMES = new Set(["warning", "note", "tip", "danger", "info", "caution"]);

/** Escapes text embedded into a raw `<summary>` HTML fragment (directive summary attribute). */
function escapeHtmlForSummary(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Whether the `open` attribute should set the native `<details open>` flag.
 * Directive parsers often yield empty string for boolean attributes.
 */
function detailsStartsOpen(attrs: Record<string, string | null | undefined>): boolean {
  const v = attrs.open;
  if (v === undefined || v === null) return false;
  if (v === "false" || v === "0") return false;
  return true;
}

/**
 * Remark plugin: maps [markdown directives](https://github.com/remarkjs/remark-directive)
 * to HTML elements via `mdast-util-to-hast` `data.hName` / `hProperties`.
 *
 * - Callouts become `<aside class="docs-callout docs-callout-{name}">…`
 * - `:::details` / `:::collapse` become `<details>`; the summary label is injected as a
 *   leading raw HTML node so `rehype-raw` can produce `<summary>` before markdown body runs.
 */
export function remarkDocFeatures() {
  return function transformDocDirectives(tree: Root): void {
    visit(tree, "containerDirective", (node: ContainerDirective) => {
      if (CALLOUT_NAMES.has(node.name)) {
        applyCalloutDirective(node);
        return;
      }

      if (node.name === "details" || node.name === "collapse") {
        applyDetailsDirective(node);
      }
    });
  };
}

function applyCalloutDirective(node: ContainerDirective): void {
  const data = (node.data ??= {});
  data.hName = "aside";
  data.hProperties = {
    className: ["docs-callout", `docs-callout-${node.name}`],
  };
}

function applyDetailsDirective(node: ContainerDirective): void {
  const attrs = node.attributes ?? {};
  const summaryRaw =
    (typeof attrs.summary === "string" && attrs.summary) ||
    (typeof attrs.title === "string" && attrs.title) ||
    "Details";
  const summaryText = String(summaryRaw);

  const data = (node.data ??= {});
  data.hName = "details";
  data.hProperties = {
    className: ["docs-collapsible"],
    ...(detailsStartsOpen(attrs) ? { open: true } : {}),
  };

  // Raw HTML must precede markdown children so rehype-raw emits <summary> before body content.
  const summaryHtml: { type: "html"; value: string } = {
    type: "html",
    value: `<summary class="docs-collapsible-summary">${escapeHtmlForSummary(summaryText)}</summary>`,
  };
  node.children = [summaryHtml, ...node.children];
}
