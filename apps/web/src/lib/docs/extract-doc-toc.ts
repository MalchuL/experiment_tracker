import { plainTextFromMarkdownHeading, slugifyHeading } from "./slugify-heading";

/** One row in the “On this page” sidebar: slug id, heading text, and outline level (1–3). */
export type DocTocItem = {
  id: string;
  text: string;
  level: number;
};

/**
 * Collects `#`–`###` headings in document order (skips fenced code blocks) for TOC links and for
 * `DocsMarkdown` heading `id`s when `toc` is passed—IDs must stay in sync with this scan.
 */
export function extractDocToc(markdown: string): DocTocItem[] {
  const items: DocTocItem[] = [];
  const usedIds = new Set<string>();
  let inFence = false;

  for (const rawLine of markdown.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (trimmed.startsWith("```")) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const m = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (!m) continue;

    const level = m[1].length;
    let text = plainTextFromMarkdownHeading(m[2].trim().replace(/\s+#+\s*$/, ""));
    const id = slugifyHeading(text, usedIds);
    items.push({ id, text, level });
  }

  return items;
}
