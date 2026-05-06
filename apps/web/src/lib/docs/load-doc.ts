import fs from "node:fs/promises";
import path from "node:path";

/**
 * Reads `apps/web/content/docs/{segments joined}.md` from the web app cwd.
 *
 * @param segments URL path under `/docs/` split into parts, e.g. `['reference','doc-features']`
 * @returns File contents, or `null` if the file is missing or unreadable
 */
export async function loadDocMarkdown(segments: string[]): Promise<string | null> {
  if (segments.length === 0) return null;
  const relativeMd = path.join(...segments) + ".md";
  const filePath = path.join(process.cwd(), "content", "docs", relativeMd);
  try {
    return await fs.readFile(filePath, "utf-8");
  } catch {
    return null;
  }
}
