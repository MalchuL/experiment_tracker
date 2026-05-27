/** Plain text used for heading labels and GitHub-style slugs. */
export function plainTextFromMarkdownHeading(text: string): string {
  return text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/<\/?[^>]+>/g, "")
    .replace(/[*~]/g, "")
    .replace(/\\([\\`*_[\]{}()#+\-.!|>])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

/** GitHub-style slug for heading anchors; keeps ids unique within the document. */
export function slugifyHeading(text: string, used: Set<string>): string {
  let base = plainTextFromMarkdownHeading(text)
    .toLowerCase()
    .trim()
    .replace(/[^\w\s\u00C0-\u024f-]/gi, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  if (!base) base = "section";
  let id = base;
  let n = 0;
  while (used.has(id)) {
    n += 1;
    id = `${base}-${n}`;
  }
  used.add(id);
  return id;
}
