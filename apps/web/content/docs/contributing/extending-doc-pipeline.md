# Extending the docs markdown pipeline

This guide is for **developers** who want to add new **rendering features** for in-app docs (new syntax blocks, components, or styling)—not for authors who only write `.md` pages (see [Adding documentation pages](/docs/contributing/adding-pages)).

## How rendering works

Rough pipeline inside [`DocsMarkdown`](../../src/components/docs/docs-markdown.tsx):

1. **Remark** (markdown → mdast): `remark-gfm`, `remark-directive`, then [`remarkDocFeatures`](../../src/lib/docs/remark-doc-features.ts) maps custom `:::name` blocks to HTML-oriented mdast (`data.hName`, `hProperties`).
2. **Remark → rehype** (mdast → hast): standard; raw `html` nodes may appear when directives inject snippets.
3. **Rehype**: `rehype-raw` expands raw HTML fragments (e.g. `<summary>` injected ahead of body), then [`rehype-sanitize`](../../src/lib/docs/docs-sanitize-schema.ts) strips anything not allowlisted.
4. **React**: `react-markdown` uses the `components` map (`aside`, `details`, `summary`, links, images, …).

Security rule: **anything new that reaches the DOM must pass `docsRehypeSanitizeSchema`** (tags + attributes). Do not widen sanitize blindly.

## Add a new container directive (e.g. `:::quote`)

1. **Parse**: `remark-directive` already enables `:::quote … :::` syntax.

2. **Transform** in [`remark-doc-features.ts`](../../src/lib/docs/remark-doc-features.ts):
   - Add the name to a set (or branch on `node.name`).
   - On `containerDirective`, set `node.data.hName` and `node.data.hProperties` (e.g. `<aside class="docs-quote">`). Children stay as markdown.
   - Follow the existing **`applyCalloutDirective`** / **`applyDetailsDirective`** pattern.

3. **Sanitize** in [`docs-sanitize-schema.ts`](../../src/lib/docs/docs-sanitize-schema.ts):
   - Add tag names to `tagNames` if you introduce new elements.
   - Add `attributes` entries for each tag (`className`, etc.).

4. **React** (if not plain HTML): in `docs-markdown.tsx`, map the element in `components` (e.g. `blockquote` or a custom tag) or reuse `aside` with a variant class and branch in a small wrapper component.

5. **CSS**: under `@layer components` in [`globals.css`](../../src/app/globals.css), scope styles under **`.docs-prose`** (e.g. `.docs-prose .docs-quote`).

6. **Docs & examples**: add samples to [Callouts, details & formatting](/docs/reference/doc-features) or a short demo section, then run **`pnpm --filter web run build`**.

## Add raw HTML fragments (advanced)

Details/collapses inject a leading **`html`** mdast node so **`rehype-raw`** can emit `<summary>` before the rest of the directive body. If you need similar behavior:

- Still escape user-controlled strings (see **`escapeHtmlForSummary`**).
- Keep fragments minimal; prefer semantic tags already allowed by sanitize.

## Change heading levels in the TOC

[`extractDocToc`](../../src/lib/docs/extract-doc-toc.ts) only scans `#`–`###`. To support `####`:

- Extend the regex and types.
- Update **`DocsMarkdown`** heading overrides (`h4`) and TOC styling in [`docs-page-shell.tsx`](../../src/components/docs/docs-page-shell.tsx) if you show level 4 in the right rail.

## New npm plugins

From **`apps/web`**:

```bash
pnpm add <package>
```

Wire plugins in **`DocsMarkdown`** in order (remark before rehype). Re-run **`pnpm --filter web run build`** and fix TypeScript if plugin typings expect a different `unified` version.

## Checklist summary

| Step | Where |
|------|--------|
| Directive → HTML mapping | `remark-doc-features.ts` |
| Allow tags/attrs | `docs-sanitize-schema.ts` |
| Custom React UI | `docs-markdown.tsx` → `components` |
| Look & feel | `globals.css` → `.docs-prose …` |
| Authoring syntax doc | `content/docs/reference/` or `contributing/` |
| Register new doc page | `docs-manifest.ts` + `content/docs/...` |

## Related

- [Adding documentation pages](/docs/contributing/adding-pages) — new URLs and manifest rows.
- [Callouts, details & formatting](/docs/reference/doc-features) — current directive syntax for authors.
