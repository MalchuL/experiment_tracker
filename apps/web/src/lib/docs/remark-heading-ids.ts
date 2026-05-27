import type { Heading, Root, RootContent } from "mdast";
import { visit } from "unist-util-visit";

import { slugifyHeading } from "./slugify-heading";

function headingText(node: Heading): string {
  const parts: string[] = [];

  function collect(child: RootContent): void {
    if ("value" in child && typeof child.value === "string") {
      parts.push(child.value);
      return;
    }
    if (child.type === "image" || child.type === "imageReference") {
      if (child.alt) parts.push(child.alt);
      return;
    }
    if ("children" in child && Array.isArray(child.children)) {
      for (const nested of child.children) {
        collect(nested as RootContent);
      }
    }
  }

  for (const child of node.children) {
    collect(child as RootContent);
  }

  return parts.join(" ");
}

/** Assign stable ids to markdown h1-h3 nodes in the same AST pass that ReactMarkdown renders. */
export function remarkHeadingIds() {
  return function transformHeadingIds(tree: Root): void {
    const usedIds = new Set<string>();

    visit(tree, "heading", (node: Heading) => {
      if (node.depth > 3) return;
      const id = slugifyHeading(headingText(node), usedIds);
      const data = (node.data ??= {});
      data.hProperties = {
        ...(typeof data.hProperties === "object" && data.hProperties !== null
          ? data.hProperties
          : {}),
        id,
      };
    });
  };
}
