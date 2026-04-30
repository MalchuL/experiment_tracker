import { defaultSchema } from "rehype-sanitize";
import type { Options as SanitizeSchema } from "rehype-sanitize";

/**
 * `rehype-sanitize` schema for doc markdown: extends GitHub-flavored defaults with tags and
 * attributes produced by callouts (`aside`) and collapsibles (`details`, `summary`), including
 * fragments expanded by `rehype-raw` from directive-injected HTML.
 */
export const docsRehypeSanitizeSchema: SanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "aside", "details", "summary"],
  attributes: {
    ...defaultSchema.attributes,
    aside: ["className"],
    details: ["className", "open"],
    summary: ["className"],
  },
};
