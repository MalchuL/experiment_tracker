# Adding documentation pages

This file is for **human authors** and **coding agents** who need to add or edit in-app documentation (`/docs/...`).

## 1. Pick the URL path

Paths map **one-to-one** to files under `apps/web/content/docs/`:

| URL | File |
|-----|------|
| `/docs/getting-started` | `content/docs/getting-started.md` |
| `/docs/getting-started/workspace` | `content/docs/getting-started/workspace.md` |
| `/docs/contributing/adding-pages` | `content/docs/contributing/adding-pages.md` |

Rules:

- Use **lowercase** segments and **hyphens** instead of spaces (`my-topic`, not `My Topic`).
- Nest folders to match nested URLs: `parent/child.md` → `/docs/parent/child`.
- One markdown file per page; the filename (without `.md`) is the **last** URL segment.

## 2. Register the page in the manifest

Edit [`apps/web/src/lib/docs/docs-manifest.ts`](../../src/lib/docs/docs-manifest.ts) and append a row to `DOCS_MANIFEST`:

```ts
{
  path: "your-section/your-page",
  title: "Human title",
  description: "Short blurb for cards and menus.",
},
```

- **`path`** must exactly match the URL under `/docs/` (no leading slash).
- **`title`** and **`description`** appear in the Topics nav and on the `/docs` index cards only; each page’s visible heading and intro still come from the markdown file (`#` title and body).
- Keep entries **sorted by path** if you prefer a tidy diff; the UI sorts for display anyway.
- **Static export**: `getStaticDocPathParams()` is derived from this list. New rows require a rebuild (or dev refresh) to prerender.

## 3. Write the markdown file

Create the file at `apps/web/content/docs/{path}.md` using `/` as directories.

- Use `#`–`###` headings; the docs UI builds **On this page** from them (code fences are ignored when scanning headings).
- Internal links: root-relative paths, e.g. `[Other page](/docs/architecture-overview)`.
- Images: put assets under `apps/web/public/docs/...` and reference with root URLs, e.g. `/docs/images/example.svg`. See [Getting started — Images](/docs/getting-started#images-in-documentation).

### Callouts (warnings, notes, …)

Supported directive names: **`warning`**, **`note`**, **`tip`**, **`danger`**, **`info`**, **`caution`**. Wrap content in triple colons; inner Markdown is rendered as usual.

```markdown
:::warning
Remember to **rebuild** after changing `DOCS_MANIFEST`.
:::

:::tip
You can nest lists and links inside a callout.
:::
```

### Collapsible sections

Use **`:::details`** or **`:::collapse`** with a **`summary`** attribute (shown on the closed row). Optional **`open`** starts expanded.

```markdown
:::details{summary="Expand deployment checklist"}

1. Set env vars.
2. Run `pnpm --filter web run build`.

:::

:::details{summary="Show defaults" open}

This block starts open.

:::
```

## 4. Verify

From the repo root:

```bash
pnpm --filter web run build
```

Open `/docs` and your new URL; confirm Topics nav, TOC anchors, and links.

## 5. Optional: repo-only notes

Files under `content/docs/` that are **not** listed in `DOCS_MANIFEST` are not served as pages. You can still add `README.md` or other notes here for agents reading the tree directly.

## For developers: new markdown features

To add **syntax or UI** for docs (directives, sanitization, components, CSS)—not just a new page—follow **[Extending the docs pipeline](/docs/contributing/extending-doc-pipeline)**.
