import { defaultSchema } from "rehype-sanitize";
import type { Options as SanitizeSchema } from "rehype-sanitize";

/**
 * `rehype-sanitize` schema for doc markdown: extends GitHub-flavored defaults with tags and
 * attributes produced by callouts (`aside`) and collapsibles (`details`, `summary`), including
 * fragments expanded by `rehype-raw` from directive-injected HTML.
 */
export const docsRehypeSanitizeSchema: SanitizeSchema = {
  ...defaultSchema,
  clobberPrefix: "",
  tagNames: [...(defaultSchema.tagNames ?? []), "aside", "details", "summary"],
  attributes: {
    ...defaultSchema.attributes,
    h1: [...((defaultSchema.attributes?.h1 as string[] | undefined) ?? []), "id"],
    h2: [...((defaultSchema.attributes?.h2 as string[] | undefined) ?? []), "id"],
    h3: [...((defaultSchema.attributes?.h3 as string[] | undefined) ?? []), "id"],
    aside: ["className"],
    details: ["className", "open"],
    summary: ["className"],
  },
};
